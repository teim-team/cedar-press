"""Exact-enterprise NEED evidence over the existing verified release transport.

A related Native entity never inherits a business's patents or debt rating.
The collection publication gate applies before even reading a release pin.
"""

from __future__ import annotations

import io
import json
import re
from urllib.parse import urlsplit

from cedar_press import repository

COMPONENTS = ("patent_observations", "credit_rating_actions", "rating_availability")
MAX_PROFILE_ROWS = 1000
MAX_ROW_BYTES = 256 * 1024


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


def select_enterprise_rows(rows, enterprise_id: str) -> list[dict]:
    """A second row-level check; only call with verified, permitted component bytes."""
    selected = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise repository.FullReleaseUnavailable("Malformed NEED evidence row")
        if row.get("enterprise_id") != enterprise_id:
            continue
        if row.get("publication_status") != "eligible" or row.get("hold_reason"):
            continue
        if not _source_url(row.get("source_url")):
            raise repository.FullReleaseUnavailable("NEED evidence lacks a source link")
        key = row.get("observation_id") or row.get("availability_id")
        if not isinstance(key, str) or not key or key in seen:
            raise repository.FullReleaseUnavailable("NEED evidence has invalid record identity")
        seen.add(key)
        selected.append(row)
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


def enterprise_evidence(enterprise_id: str) -> dict:
    """Use one pinned release, exact object identity and the shared publication gate."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", enterprise_id):
        raise ValueError("Malformed enterprise identifier")
    if enterprise_id.startswith("CE-"):
        return empty_profile(
            "enterprise_required",
            "Patents and ratings belong to the exact enterprise or legal issuer. "
            "An affiliated Native entity does not inherit them.",
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
        "no_evidence", "No permitted evidence for this exact enterprise in this release."
    )
    result["release_id"] = pin["release_id"]
    for component in COMPONENTS:
        release = repository.grove_full_release("need", pin["release_id"], component=component)
        stream = release.get("content_file") or release.get("spool")
        if stream is None and isinstance(release.get("content"), bytes):
            stream = io.BytesIO(release["content"])
        if stream is None:
            raise repository.FullReleaseUnavailable("NEED requires a verified component stream")
        try:
            if release["release_id"] != pin["release_id"]:
                raise repository.FullReleaseUnavailable("NEED profile release changed")
            result[component] = select_enterprise_rows(_rows(stream), enterprise_id)
        finally:
            stream.close()
    if any(result[name] for name in COMPONENTS):
        result.update(
            status="available",
            message=(
                "Source observations for this exact enterprise. Historical ratings are not "
                "verified "
                "current ratings; an acquisition does not by itself prove a patent assignment."
            ),
        )
    return result
