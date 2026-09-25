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


def is_grove_release(collection_id: str) -> bool:
    """Whether ``collections.GROVE_RELEASE_COLLECTIONS`` declares this collection."""
    return any(entry["id"] == collection_id for entry in launch.GROVE_RELEASE_COLLECTIONS)


def may_download_full(tier: str, collection_id: str) -> bool:
    """Whether this plan may take a pinned full release of this collection.

    The storefront rule (``may_open``) for every Press collection, unchanged.
    For a collection the reviewed Grove declaration names, the same shelf rule
    with the ``grove`` shelf: ``grove`` and ``tree`` reach it, ``press`` and
    ``press_pro`` do not. ``may_open`` itself still refuses Grove collections
    to every tier, so the shelf, the sample and Ask are unaffected.
    """
    if may_open(tier, collection_id):
        return True
    return is_grove_release(collection_id) and _reaches(tier, "grove")


#: A component id is the field-map key's part after the slash (a table stem);
#: the same shape ``code/build.py release_dataset_id`` accepts.
_COMPONENT_ID = re.compile(r"[a-z0-9][a-z0-9_]{0,59}")
GROVE_COMPONENT_SEPARATOR = "--"


def _field_map_tables() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "data/cedar/field_map.json"
    return json.loads(path.read_text(encoding="utf-8"))["tables"]


def grove_components(collection_id: str) -> tuple[str, ...]:
    """A declared Grove collection's governed components, in field-map order.

    Empty for anything the Grove declaration does not name. A component the
    catalog does not pin is still listed here and is refused at download.
    """
    if not is_grove_release(collection_id):
        return ()
    prefix = collection_id + "/"
    return tuple(
        key[len(prefix) :]
        for key, entry in _field_map_tables().items()
        if key.startswith(prefix)
        and entry.get("collection") == collection_id
        and _COMPONENT_ID.fullmatch(key[len(prefix) :])
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



#: THE Cedar Grove release pin: the one file naming the immutable Lumecon-data
#: COLLECTION release Cedar serves for each declared Grove collection. It
#: extends the existing ``CEDAR_GROVE_RELEASE_CATALOG`` mechanism rather than
#: replacing it: that variable still says where the reviewed catalog's bytes
#: are, and this committed pin says WHICH bytes they must be (catalog SHA-256
#: and catalog_id) and which one release inside them (release_id and the
#: collection-manifest SHA-256). A catalog, manifest or artifact that differs is
#: refused; nothing falls back to a sample, a local CSV, a branch or a
#: ``current`` pointer. Changing what Cedar serves is a reviewed edit of this
#: file; rollback is the revert of that edit, and every component moves with it.
GROVE_RELEASE_PIN = Path(__file__).resolve().parents[2] / "data/cedar/grove_release_pin.json"
GROVE_RELEASE_CATALOG_ENV = "CEDAR_GROVE_RELEASE_CATALOG"
#: Lumecon release classes this server delivers. A rehearsal (real candidate,
#: PROPOSED IDs) and a synthetic fixture never reach a customer; only the
#: consumer tests widen these two settings, explicitly.
GROVE_SERVED_RELEASE_CLASSES: frozenset[str] = frozenset({"production"})
GROVE_SERVE_SYNTHETIC = False
#: The one switch that lets a REHEARSAL (real candidate, PROPOSED IDs) be
#: served: ``CEDAR_GROVE_ENVIRONMENT=review``, mirroring Lumecon-data's
#: ``LUMECON_ENVIRONMENT=review``. Unset or ``production`` serves production
#: releases only. ``review`` is refused outright when
#: ``CEDAR_PRESS_ENVIRONMENT=production`` (nothing is served, not even the
#: production release), and any other value is refused, so a typo or a review
#: flag leaking into production fails closed rather than widening delivery.
#: A synthetic fixture stays unservable in review too (``GROVE_SERVE_SYNTHETIC``).
GROVE_ENVIRONMENT_ENV = "CEDAR_GROVE_ENVIRONMENT"
GROVE_REVIEW_RELEASE_CLASSES: frozenset[str] = frozenset({"rehearsal"})


def grove_served_release_classes() -> frozenset[str]:
    """Release classes this process may deliver, from the explicit Grove setting."""
    mode = os.environ.get(GROVE_ENVIRONMENT_ENV, "") or "production"
    if mode == "production":
        return GROVE_SERVED_RELEASE_CLASSES
    if mode != "review":
        raise FullReleaseUnavailable("Unknown Grove release environment")
    if os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") == "production":
        raise FullReleaseUnavailable("Rehearsal review is never enabled in production")
    return GROVE_SERVED_RELEASE_CLASSES | GROVE_REVIEW_RELEASE_CLASSES
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PIN_KEYS = {"catalog_id", "catalog_sha256", "collection_id", "release_id", "manifest_sha256"}


class GroveReleaseNotPinned(FullReleaseUnavailable):
    """No immutable release is pinned for this Grove collection (production until issuance)."""


def grove_release_pin(collection_id: str) -> dict[str, str]:
    """The reviewed pin for one Grove collection, strictly shaped, or a refusal.

    Exactly one collection release: the pinned ``collection_id`` IS the Grove
    collection. A per-table dataset (``<collection>--<table>``) is never
    assembled into a collection, so a pin naming one is refused.
    """
    try:
        document = json.loads(GROVE_RELEASE_PIN.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FullReleaseUnavailable("Grove release pin unreadable") from error
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("product") != "cedar_grove"
        or not isinstance(document.get("pins"), dict)
    ):
        raise FullReleaseUnavailable("Malformed Grove release pin")
    pin = document["pins"].get(collection_id)
    if pin is None:
        raise GroveReleaseNotPinned(
            f"No Lumecon {collection_id} release is pinned; unavailable until one is issued"
        )
    if (
        not isinstance(pin, dict)
        or set(pin) != _PIN_KEYS
        or not all(isinstance(pin[key], str) for key in _PIN_KEYS)
        or not all(_SHA256.fullmatch(pin[key]) for key in _PIN_KEYS - {"collection_id"})
    ):
        raise FullReleaseUnavailable("Malformed Grove release pin")
    if pin["collection_id"] != collection_id:
        raise FullReleaseUnavailable(
            "A Grove pin names one collection release, never a per-table release"
        )
    return dict(pin)


def _grove_prefix(pin: dict[str, str]) -> str:
    return f"/v1/collections/{pin['collection_id']}/releases/{pin['release_id']}"


def _grove_catalog(pin: dict[str, str]) -> dict[str, Any]:
    """The pinned catalog's one entry for the pinned release, verified by hash."""
    location = os.environ.get(GROVE_RELEASE_CATALOG_ENV)
    if not location:
        raise FullReleaseUnavailable("No pinned release catalog configured")
    raw = Path(location).read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin["catalog_sha256"]:
        raise FullReleaseUnavailable("Catalog differs from the pinned catalog")
    catalog = json.loads(raw)
    if not isinstance(catalog, dict):
        raise FullReleaseUnavailable("Malformed catalog")
    catalog_id = catalog.pop("catalog_id", None)
    if (
        catalog_id != pin["catalog_id"]
        or hashlib.sha256(_canonical_bytes(catalog)).hexdigest() != catalog_id
    ):
        raise FullReleaseUnavailable("Catalog checksum mismatch")
    if (
        type(catalog.get("schema_version")) is not int
        or catalog["schema_version"] != 1
        or catalog.get("product") != "cedar_grove"
        or catalog.get("entitlement_required") is not True
    ):
        raise FullReleaseUnavailable("Wrong product catalog")
    # A dataset catalog of per-table releases is not a collection release,
    # however its dataset IDs are spelled.
    if catalog.get("catalog_kind") != "collection_releases" or "collections" in catalog:
        raise FullReleaseUnavailable("Per-table releases cannot stand in for a collection release")
    entries = catalog.get("collection_releases")
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise FullReleaseUnavailable("Malformed catalog entries")
    mine = [item for item in entries if item.get("collection_id") == pin["collection_id"]]
    if len(mine) != 1:
        raise FullReleaseUnavailable("Exactly one pinned collection release required")
    entry = mine[0]
    if (
        entry.get("release_id") != pin["release_id"]
        or entry.get("manifest_sha256") != pin["manifest_sha256"]
        or entry.get("manifest_path") != _grove_prefix(pin) + "/manifest"
    ):
        raise FullReleaseUnavailable("Catalog entry differs from the pinned release")
    return entry


def _grove_manifest(pin: dict[str, str]) -> dict[str, Any]:
    """The one collection-level manifest, byte-verified against the pin."""
    manifest = _release_json(_grove_prefix(pin) + "/manifest")
    if not isinstance(manifest, dict):
        raise FullReleaseUnavailable("Malformed manifest")
    if hashlib.sha256(_canonical_bytes(manifest)).hexdigest() != pin["manifest_sha256"]:
        raise FullReleaseUnavailable("Manifest differs from the pinned release")
    if (
        manifest.get("collection_id") != pin["collection_id"]
        or manifest.get("release_id") != pin["release_id"]
        or manifest.get("release_kind") != "collection"
        or manifest.get("product") != "cedar_grove"
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or not isinstance(manifest.get("components"), dict)
    ):
        raise FullReleaseUnavailable("Malformed collection manifest")
    if manifest.get("release_class") not in grove_served_release_classes() or (
        manifest.get("synthetic") is not False and not GROVE_SERVE_SYNTHETIC
    ):
        raise FullReleaseUnavailable("Release is not eligible for customer delivery")
    _grove_partitioned_parts(manifest)
    return manifest


def _grove_partitioned_parts(manifest: dict[str, Any]) -> frozenset[str]:
    """Every component name that belongs to a partitioned (bounded-parts) component.

    Lumecon ships a large table (Gaming payments) as ordinary part components
    plus one ``partitioned_components`` entry naming them. Cedar never assembles
    parts and serves none of them today. The declaration must still agree with
    the part entries of this same pinned manifest (every part present, its
    record count and ``records.jsonl`` hash identical, the logical count their
    sum); any disagreement is an incomplete or unverified release, refused whole.
    """
    declared = manifest.get("partitioned_components", [])
    if not isinstance(declared, list):
        raise FullReleaseUnavailable("Malformed partitioned components")
    names: set[str] = set()
    for logical in declared:
        parts = logical.get("parts") if isinstance(logical, dict) else None
        name = logical.get("name") if isinstance(logical, dict) else None
        if not isinstance(name, str) or name in manifest["components"] or not parts:
            raise FullReleaseUnavailable("Malformed partitioned components")
        if not isinstance(parts, list):
            raise FullReleaseUnavailable("Malformed partitioned components")
        total = 0
        for part in parts:
            component = part.get("component") if isinstance(part, dict) else None
            entry = manifest["components"].get(component) if isinstance(component, str) else None
            if (
                not isinstance(entry, dict)
                or component in names
                or type(part.get("record_count")) is not int
                or part["record_count"] != entry.get("record_count")
                or part.get("records.jsonl") != (entry.get("files") or {}).get("records.jsonl")
            ):
                raise FullReleaseUnavailable(
                    "Partitioned component parts are incomplete or unverified"
                )
            total += part["record_count"]
            names.add(component)
        if logical.get("record_count") != total:
            raise FullReleaseUnavailable("Partitioned component parts are incomplete or unverified")
        names.add(name)
    return frozenset(names)


def grove_component_contract(manifest: dict[str, Any], collection_id: str, component: str):
    """One component's embedded contract, checked against Cedar's presentation
    entry ``<collection>/<component>`` in the field map (no schema copy here:
    the field map may only present what the pinned contract declares)."""
    if component in _grove_partitioned_parts(manifest):
        # Parts are never assembled here, and no part is presented today.
        raise FullReleaseUnavailable("A partitioned component is not served by Cedar")
    contract = manifest["components"].get(component)
    if not isinstance(contract, dict):
        raise FullReleaseUnavailable("Component is not in the pinned release")
    rights = contract.get("rights")
    if (
        not isinstance(rights, dict)
        or rights.get("publication_class") not in {"public", "publishable"}
        or rights.get("redistribution") is not True
        or contract.get("download_permitted") is not True
    ):
        raise FullReleaseUnavailable("Component is not eligible for customer delivery")
    fields = contract.get("fields")
    if not isinstance(fields, list) or any(not isinstance(f, dict) for f in fields):
        raise FullReleaseUnavailable("Malformed component contract")
    header = [field.get("name") for field in fields]
    entry = _field_map_tables().get(f"{collection_id}/{component}")
    if not entry or entry.get("collection") != collection_id or header != entry.get("order"):
        raise FullReleaseUnavailable("Full release does not match product field map")
    declared_rights = (contract.get("metadata") or {}).get("field_rights") or {}
    for item in entry.get("fields", []):
        if (
            item.get("decision") in {"keep", "rename"}
            and item["column"] in declared_rights
            and item.get("rights_class") != declared_rights[item["column"]]
        ):
            raise FullReleaseUnavailable("Field-map rights differ from the pinned contract")
    primary_key = contract.get("primary_key")
    if not isinstance(primary_key, list) or not primary_key or not set(primary_key) <= set(header):
        raise FullReleaseUnavailable("Missing declared row identity")
    expected = (contract.get("files") or {}).get("records.jsonl") or {}
    count = contract.get("record_count")
    if (
        type(count) is not int
        or count < 1
        or type(expected.get("bytes")) is not int
        or not 0 < expected["bytes"] <= MAX_RELEASE_BYTES
        or not isinstance(expected.get("sha256"), str)
        or not _SHA256.fullmatch(expected["sha256"])
    ):
        raise FullReleaseUnavailable("Invalid or oversized release artifact")
    return contract, header, primary_key, count, expected


def grove_full_release(
    collection_id, requested_release_id=None, *, component=None, metadata_only=False
):
    """One authorized component of the ONE pinned Lumecon release of a Grove collection.

    Order: declared collection, offered component, publication hold, pin,
    pinned catalog bytes, pinned collection manifest, the component's embedded
    contract against the field map, then (unless ``metadata_only``) the exact
    component bytes. Any mismatch fails closed; nothing is substituted.
    """
    if not is_grove_release(collection_id):
        raise FullReleaseUnavailable("Unknown collection")
    if not isinstance(component, str) or not _COMPONENT_ID.fullmatch(component):
        raise FullReleaseUnavailable("A Grove release names a well-formed component")
    if component not in grove_components(collection_id):
        raise FullReleaseUnavailable("Component is not offered for this collection")
    try:
        policy = _publication_policy()
    except (OSError, ImportError, AttributeError) as error:
        raise FullReleaseUnavailable("Publication policy unavailable") from error
    try:
        policy.assert_collection_publishable(collection_id)
    except policy.FieldMapRefusal as error:
        raise FullReleaseUnavailable("Collection publication is held") from error
    try:
        pin = grove_release_pin(collection_id)
        release_id = pin["release_id"]
        if not metadata_only and requested_release_id != release_id:
            raise FullReleaseUnavailable("Requested release is not the approved catalog pin")
        _grove_catalog(pin)
        manifest = _grove_manifest(pin)
        _contract, header, primary_key, count, expected = grove_component_contract(
            manifest, collection_id, component
        )
        route = (
            f"/press/collections/{collection_id}/full-download"
            f"?release_id={release_id}&component={component}"
        )
        if metadata_only:
            return {
                "kind": "full",
                "release_id": release_id,
                "schema_version": 1,
                "record_count": count,
                "fields": header,
                "table_id": component,
                "scope": "One governed component of a Cedar Grove collection release",
                "format": "jsonl",
                "records_sha256": expected["sha256"],
                "download_path": route,
            }
        content = _release_bytes(
            _grove_prefix(pin) + f"/components/{component}/download", limit=expected["bytes"]
        )
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
            "component": component,
            "citation": f"Cedar Grove {collection_id}/{component}, release {release_id}",
            "filename": f"{collection_id}--{component}-{release_id}.jsonl",
            "media_type": "application/x-ndjson",
        }
    except FullReleaseUnavailable:
        raise
    except (OSError, HTTPException, ValueError, KeyError, TypeError) as error:
        raise FullReleaseUnavailable(
            "Pinned full release unavailable or failed verification"
        ) from error


def grove_release_metadata(collection_id):
    """The landing page's descriptors: one verified entry per governed component.

    ``None`` when no release is pinned; an unverifiable component is reported
    as unavailable rather than dropped, and never replaced by a sample.
    """
    if not is_grove_release(collection_id):
        return None
    out = []
    for component in grove_components(collection_id):
        try:
            out.append(grove_full_release(collection_id, component=component, metadata_only=True))
        except GroveReleaseNotPinned:
            return None
        except FullReleaseUnavailable:
            out.append({"kind": "full", "table_id": component, "status": "unavailable"})
    return out


def full_release_metadata(collection_id):
    """Preview counts are never substituted for a verified full-release descriptor."""
    if not os.environ.get("CEDAR_PRESS_RELEASE_CATALOG"):
        return None
    try:
        return full_release(collection_id, metadata_only=True)
    except FullReleaseUnavailable:
        return {"kind": "full", "status": "unavailable"}
