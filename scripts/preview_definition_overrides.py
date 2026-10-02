"""Validate evidence-pinned, maintained preview definition overrides."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Callable

_LIMIT = 8 * 1024 * 1024
_EVIDENCE_LIMIT = 32 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate override JSON key: " + key)
        result[key] = value
    return result


def _digest(path: Path, mode: str) -> str:
    with path.open("rb") as stream:
        data = stream.read(_EVIDENCE_LIMIT + 1)
    if len(data) > _EVIDENCE_LIMIT:
        raise ValueError("Override evidence file exceeds bound")
    if mode != "raw":
        raise ValueError("Unsupported evidence hash mode")
    return hashlib.sha256(data).hexdigest()


def _git_environment() -> dict[str, str]:
    # Bind object lookup to the selected checkout, not an inherited Git directory.
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
    ):
        env.pop(key, None)
    env.update(
        GIT_NO_LAZY_FETCH="1",
        GIT_ALLOW_PROTOCOL="",
        GIT_TERMINAL_PROMPT="0",
        GIT_OPTIONAL_LOCKS="0",
    )
    return env


def _git_command(root: Path, *args: str) -> list[str]:
    return ["git", "--no-replace-objects", "-C", str(root), "cat-file", *args]


def _git_object_info(root: Path, query: str) -> tuple[str, str, int]:
    # One newline-free query yields only an object ID, type and decimal size.
    # In the missing-object case Git echoes the bounded query, never blob bytes.
    try:
        result = subprocess.run(
            _git_command(root, "--batch-check=%(objectname) %(objecttype) %(objectsize)"),
            input=(query + "\n").encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_environment(),
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(
            "Pinned evidence requires local Git objects; ensure Git is installed "
            "and provide a checkout containing the pinned commit and path"
        ) from exc
    match = re.fullmatch(
        rb"([0-9a-f]{40}|[0-9a-f]{64}) (blob|tree|commit|tag) ([0-9]{1,20})\n",
        result.stdout,
    )
    if result.returncode != 0 or match is None:
        raise ValueError(
            "Pinned evidence object is unavailable locally: "
            + query
            + "; provide a checkout containing the pinned commit and path "
            "(no network fetch or working-tree fallback)"
        )
    return match[1].decode("ascii"), match[2].decode("ascii"), int(match[3])


def _pinned_digest(root: Path, revision: str, relative: str) -> str:
    commit, kind, _ = _git_object_info(root, revision)
    if commit != revision or kind != "commit":
        raise ValueError("Evidence revision is not a full local commit: " + revision)
    blob, kind, size = _git_object_info(root, revision + ":" + relative)
    if kind != "blob":
        raise ValueError("Pinned evidence path is not a blob: " + relative)
    if size > _EVIDENCE_LIMIT:
        raise ValueError("Override evidence blob exceeds bound")
    try:
        process = subprocess.Popen(
            _git_command(root, "blob", blob),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_environment(),
        )
    except OSError as exc:
        raise ValueError("Could not read pinned evidence from local Git objects") from exc
    try:
        assert process.stdout is not None
        digest = hashlib.sha256()
        remaining = size
        while remaining:
            chunk = process.stdout.read(min(64 * 1024, remaining))
            if not chunk:
                raise ValueError("Pinned evidence blob is truncated or unavailable locally")
            digest.update(chunk)
            remaining -= len(chunk)
        if process.stdout.read(1):
            raise ValueError("Pinned evidence blob exceeds its declared bound")
        if process.wait(timeout=15) != 0:
            raise ValueError("Pinned evidence blob could not be read locally")
        return digest.hexdigest()
    except subprocess.SubprocessError as exc:
        raise ValueError("Local pinned evidence read did not complete") from exc
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=15)


def load(
    repo: Path,
    producer: Path | None,
    *,
    is_substantive: Callable[[Any, str], bool],
) -> dict[str, dict[str, dict[str, Any]]]:
    repo = Path(repo).resolve(strict=True)
    file = repo / "data/cedar/preview_definition_overrides.json"
    if not file.exists():
        return {}
    with file.open("rb") as stream:
        raw = stream.read(_LIMIT + 1)
    if len(raw) > _LIMIT:
        raise ValueError("Preview definition overrides exceed bound")
    document = json.loads(raw, object_pairs_hook=_unique_object)
    if (
        not isinstance(document, dict)
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
    ):
        raise ValueError("Unsupported preview definition override schema")
    if set(document) - {"schema_version", "evidence", "collections", "_note"}:
        raise ValueError("Unknown override top-level key")
    evidence = document.get("evidence")
    collections = document.get("collections")
    if not isinstance(evidence, dict) or not isinstance(collections, dict):
        raise ValueError("Override evidence and collections must be mappings")
    roots = {
        "press": repo,
        "producer": Path(producer).resolve(strict=True) if producer else None,
    }
    verified = {}
    for evidence_id, entry in evidence.items():
        if (
            not isinstance(evidence_id, str)
            or not evidence_id
            or not isinstance(entry, dict)
        ):
            raise ValueError("Malformed override evidence entry")
        if set(entry) - {"repository", "path", "sha256", "revision", "hash_mode"}:
            raise ValueError("Unknown override evidence key: " + evidence_id)
        repository = entry.get("repository")
        relative = entry.get("path")
        expected = entry.get("sha256")
        revision = entry.get("revision")
        mode = entry.get("hash_mode", "raw")
        if (
            not isinstance(repository, str)
            or repository not in roots
            or roots[repository] is None
        ):
            raise ValueError(
                "Producer evidence requires --producer or the staging producer checkout"
            )
        if (
            not isinstance(relative, str)
            or "\\" in relative
            or len(relative) > 4096
            or any(ord(char) < 32 or ord(char) == 127 for char in relative)
        ):
            raise ValueError("Evidence paths must be relative POSIX paths")
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or not pure.parts
            or ".." in pure.parts
            or ":" in relative
        ):
            raise ValueError("Evidence path escapes its repository")
        if (
            not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None
        ):
            raise ValueError("Evidence SHA-256 must be explicit")
        if (
            not isinstance(revision, str)
            or revision != "working-tree"
            and re.fullmatch(r"[0-9a-f]{40}", revision) is None
        ):
            raise ValueError("Evidence revision must be a full commit or working-tree")
        root = roots[repository]
        assert root is not None
        if mode != "raw":
            raise ValueError("Unsupported evidence hash mode")
        if revision == "working-tree":
            path = root.joinpath(*pure.parts).resolve(strict=True)
            if not path.is_relative_to(root):
                raise ValueError("Evidence symlink escapes its repository")
            actual = _digest(path, mode)
        else:
            actual = _pinned_digest(root, revision, relative)
        if actual != expected:
            raise ValueError("Preview definition evidence changed: " + evidence_id)
        verified[evidence_id] = {**entry, "hash_mode": mode}
    resolved = {}
    override_hash = hashlib.sha256(raw).hexdigest()
    for collection, fields in collections.items():
        if (
            not isinstance(collection, str)
            or re.fullmatch(r"[a-z0-9-]+", collection) is None
            or not isinstance(fields, dict)
        ):
            raise ValueError("Malformed collection override mapping")
        current = {}
        for column, definition in fields.items():
            if (
                not isinstance(column, str)
                or not column
                or not isinstance(definition, dict)
            ):
                raise ValueError("Malformed field override mapping")
            if set(definition) - {"meaning", "label", "evidence", "definition_source"}:
                raise ValueError("Unknown field override key: " + column)
            if not is_substantive(definition.get("meaning"), column):
                raise ValueError("Substantive override meaning required: " + column)
            label = definition.get("label", column.replace("_", " "))
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Override label must be nonblank")
            references = definition.get("evidence")
            if (
                not isinstance(references, list)
                or not references
                or any(
                    not isinstance(ref, str) or ref not in verified
                    for ref in references
                )
                or len(set(references)) != len(references)
            ):
                raise ValueError(
                    "Override must reference unique verified evidence: " + column
                )
            source = definition.get("definition_source")
            if (
                not isinstance(source, dict)
                or source.get("kind") != "reviewed_transform_contract"
            ):
                raise ValueError(
                    "Override requires reviewed_transform_contract provenance"
                )
            if source.get("path") not in {verified[ref]["path"] for ref in references}:
                raise ValueError(
                    "Definition source path is not covered by evidence: " + column
                )
            if source.get("revision") not in {
                verified[ref]["revision"]
                for ref in references
                if verified[ref]["path"] == source["path"]
            }:
                raise ValueError(
                    "Definition source revision is not covered by evidence: " + column
                )
            current[column] = {
                "column": column,
                "label": label,
                "meaning": definition["meaning"],
                "definition_source": {
                    **source,
                    "evidence": [{"id": ref, **verified[ref]} for ref in references],
                    "override_file": "data/cedar/preview_definition_overrides.json",
                    "override_file_sha256": override_hash,
                    "override_key": f"{collection}.{column}",
                },
            }
        resolved[collection] = current
    return resolved
