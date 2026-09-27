"""NEED evidence on registered Native entity profiles.

A related Native entity never inherits a business's patents or debt rating.
The collection publication gate applies before even reading a release pin.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from cedar_press import repository

COMPONENTS = ("patent_observations", "credit_rating_actions", "rating_availability")
MAX_PROFILE_ROWS = 1000
MAX_ROW_BYTES = 256 * 1024
REGISTER_PATH = Path(__file__).resolve().parents[2] / "public/data/cedar/register.json"


class UnregisteredEntity(ValueError):
    """A NEED record alone does not create a public entity profile."""


def registered_entity(cedar_uid: str) -> str | None:
    """The existing published projection of the internal entity register."""
    try:
        with REGISTER_PATH.open("rb") as stream:
            content = stream.read(4 * 1024 * 1024 + 1)
        if len(content) > 4 * 1024 * 1024:
            raise ValueError("Oversized register")
        matches = [row for row in json.loads(content)["entities"] if row[0] == cedar_uid]
        if len(matches) > 1:
            raise ValueError("Duplicate registered entity")
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        raise repository.FullReleaseUnavailable("Entity register unavailable") from error
    if not matches:
        raise UnregisteredEntity("No registered Native entity with that identifier")
    return matches[0][1]


def empty_profile(status: str, message: str) -> dict:
    return {
        "status": status,
        "message": message,
        "release_id": None,
        **{name: [] for name in COMPONENTS},
    }


def _source_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def select_entity_rows(rows, cedar_uid: str, links: dict[str, list[dict]]) -> list[dict]:
    """A second row-level check; only call with verified, permitted component bytes."""
    selected = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise repository.FullReleaseUnavailable("Malformed NEED evidence row")
        direct = row.get("legal_subject_cedar_uid") == cedar_uid
        relationship = links.get(row.get("enterprise_id"))
        if not direct and relationship is None:
            continue
        if row.get("publication_status") != "eligible" or row.get("hold_reason"):
            continue
        if not _source_url(row.get("source_url")):
            raise repository.FullReleaseUnavailable("NEED evidence lacks a source link")
        key = row.get("observation_id") or row.get("availability_id")
        if not isinstance(key, str) or not key or key in seen:
            raise repository.FullReleaseUnavailable("NEED evidence has invalid record identity")
        seen.add(key)
        selected.append(
            {
                **row,
                "profile_attribution": {
                    "kind": "registered_entity" if direct else "related_enterprise",
                    "profile_cedar_uid": cedar_uid,
                    "relationships": [] if direct else relationship,
                },
            }
        )
        if len(selected) > MAX_PROFILE_ROWS:
            raise repository.FullReleaseUnavailable("NEED profile exceeds its response limit")
    return selected


def _rows(stream):
    while line := stream.readline(MAX_ROW_BYTES + 1):
        if len(line) > MAX_ROW_BYTES:
            raise repository.FullReleaseUnavailable("Oversized NEED evidence row")
        try:
            yield json.loads(line)
        except (ValueError, UnicodeDecodeError) as error:
            raise repository.FullReleaseUnavailable("Malformed NEED evidence bytes") from error


def _component_rows(component: str, release_id: str):
    release = repository.grove_full_release("need", release_id, component=component)
    stream = release.get("content_file") or release.get("spool")
    if stream is None and isinstance(release.get("content"), bytes):
        stream = io.BytesIO(release["content"])
    if stream is None:
        raise repository.FullReleaseUnavailable("NEED requires a verified component stream")
    try:
        if release["release_id"] != release_id:
            raise repository.FullReleaseUnavailable("NEED profile release changed")
        yield from _rows(stream)
    finally:
        stream.close()


def entity_evidence(cedar_uid: str) -> dict:
    """Direct entity facts and attributed related enterprises, never duplicate profiles."""
    if not re.fullmatch(r"CE-[A-Z0-9]+-[A-Z0-9]{2}", cedar_uid):
        raise UnregisteredEntity("Profiles require a registered Cedar entity ID")
    name = registered_entity(cedar_uid)
    if name is None:
        return empty_profile(
            "identity_held", "This entity's identity is withheld from publication."
        )
    try:
        policy = repository._publication_policy()
    except (OSError, ImportError, AttributeError) as error:
        raise repository.FullReleaseUnavailable("NEED publication policy unavailable") from error
    try:
        policy.assert_collection_publishable("need")
    except policy.FieldMapRefusal:
        return empty_profile(
            "publication_held",
            "NEED enterprise evidence is under publication review. "
            "No published patent or rating facts are available here yet.",
        )
    pin = repository.grove_release_pin("need")
    result = empty_profile(
        "no_evidence", "No permitted NEED evidence for this entity in this release."
    )
    result["release_id"] = pin["release_id"]
    result["profile_cedar_uid"] = cedar_uid
    links: dict[str, list[dict]] = {}
    seen_links = set()
    profile_links = []
    for link in _component_rows("profile_links", pin["release_id"]):
        if not isinstance(link, dict):
            raise repository.FullReleaseUnavailable("Malformed NEED profile relationship")
        if link.get("profile_cedar_uid") != cedar_uid:
            continue
        if link.get("publication_status") != "eligible" or link.get("hold_reason"):
            continue
        if (
            not link.get("enterprise_id")
            or not link.get("enterprise_name")
            or not link.get("relationship_type")
            or not _source_url(link.get("source_url"))
        ):
            raise repository.FullReleaseUnavailable("Unsubstantiated NEED profile relationship")
        key = link.get("profile_link_id")
        if (
            not isinstance(key, str)
            or not key
            or key in seen_links
            or len(seen_links) >= MAX_PROFILE_ROWS
        ):
            raise repository.FullReleaseUnavailable("Ambiguous or oversized NEED profile links")
        seen_links.add(key)
        links.setdefault(link["enterprise_id"], []).append(link)
        profile_links.append(link)
    result["related_enterprises"] = profile_links
    for component in COMPONENTS:
        result[component] = select_entity_rows(
            _component_rows(component, pin["release_id"]), cedar_uid, links
        )
    if any(result[name] for name in COMPONENTS):
        result.update(
            status="available",
            message=(
                "Facts retain their exact legal owner or issuer, including related enterprises. "
                "Historical ratings are not "
                "verified "
                "current ratings; an acquisition does not by itself prove a patent assignment."
            ),
        )
    return result
