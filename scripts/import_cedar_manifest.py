#!/usr/bin/env python3
"""Import Cedar's measured descriptors and sample rows into the product repo.

    py -3 scripts/import_cedar_manifest.py [--workspace "<path to data workspace>"]

``--workspace`` defaults to THIS REPOSITORY, because since the consolidation
the data workspace and the product site are one tree. See
``_default_workspace()`` for the pre-consolidation case that is still handled.

WHAT THIS CLOSES
----------------
``server/cedar_press/collections.py`` shipped four hand-written datasets and
said so in its own docstring:

    PROTOTYPE LIMITATIONS -- Every number in this file is demonstration data
    ... **The real pilot datasets arrive as manifest + data files and replace
    the inline series here.**

This is the importer for that manifest and those data files. It reads three
outputs of the Cedar data workspace and writes one file both language
implementations load:

  ``dist/collection_descriptors.json``        code/760_collection_descriptors.py
  ``dist/collection_descriptors.cedar.json``  the same script's sibling
  ``dist/review/MANIFEST.csv``                code/1135_full_dataset_review_bundle.py
  ``dist/review/samples/<c>/<t>__10.csv``     the same script, ten rows a table

WHY A MANIFEST RATHER THAN TWO EDITED MODULES
---------------------------------------------
``collections.py`` and ``src/features/grove/collection.js`` are required to
hold the same values, and the Python docstring claimed a test enforced that.
No such test existed and the two had already drifted: the Python descriptor
carried ``shelf`` and the JavaScript one did not, and the JavaScript citation
resolved its version through ``pressReleases.js`` while the Python one read
the descriptor. Editing two literals in two languages is what produced that.
Both modules now read THIS file, so a value cannot differ, and
``server/tests/test_collection.py`` runs both implementations and compares
them anyway.

NO NUMBER IS INVENTED HERE, AND NO NUMBER IS FILLED IN
-------------------------------------------------------
Every value written is copied from the workspace outputs above. Where Cedar
has no measurement the field is written ``null`` and named in
``unmeasured_fields`` with the reason, rather than carrying a demonstration
value forward into a slot that would read as real:

  ``vintage``    760 emits an empty string for all fifteen collections; the
                 cadence measurement it derives vintage from produced nothing.
  ``downloads``  a platform metric. 760's docstring: "It lives in the platform
                 database and Cedar has no business inventing it."

TWELVE, NOT FIFTEEN
-------------------
Cedar measures fifteen collections. Three do not go on the storefront, and
each is listed in ``excluded`` with its reason rather than silently dropped:
``newsletters`` (owner ruling, 2026-09-02), ``gaming`` (shelf ``grove``: built
for Cedar Grove and still in progress, so the storefront neither sells nor
previews it, owner ruling 2026-09-04) and ``_entity_layer`` (shelf
``infrastructure``). ``server/tests/test_collection.py`` compares
``STOREFRONT`` and ``EXCLUDED`` here against the manifest on disk, so a reason
edited in one place and not regenerated in the other fails a test.
Excluding a collection from the storefront is not deleting its data: the
workspace keeps every one of them, and this script only chooses what the
product shows.

THE FULL SPREADSHEETS ARE REFERENCED, NEVER COPIED
--------------------------------------------------
1135 also writes ``dist/review/spreadsheets/``, measured at 6.2 GB. GitHub
refuses a file over 100 MB and this repository is the wrong home for the
data regardless. Only the ten-row samples are copied (1.4 MB across the
twelve). Every full table is described in the manifest -- its row count, how
many files it splits into and the largest of them -- so a serving layer can
find it, and ``full_files.served`` is ``false`` so nothing claims otherwise.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: The manifest 1135 writes and this script reads. Its presence is what says a
#: directory IS a Cedar data workspace, rather than a directory next to one.
WORKSPACE_MARKER = Path("dist") / "review" / "MANIFEST.csv"


def _default_workspace() -> Path:
    """Where Cedar's ``dist/`` lives when ``--workspace`` is not given.

    SINCE THE CONSOLIDATION THE ANSWER IS THIS REPOSITORY, and the default
    said otherwise. The product site and the data workspace used to be two
    checkouts sitting side by side, so ``REPO.parent`` was right; they are one
    tree now. An ordinary consolidated checkout -- ``/workspace/cedar-press``,
    or ``Desktop/Cedar Press`` -- has no name beginning with ``agent-``, so the
    no-argument command this module's own docstring documents searched the
    checkout's PARENT and died on
    ``missing input: <parent>/dist/collection_descriptors.json``. Measured
    2026-09-02 from ``scratchpad/consolidate``: it looked in
    ``scratchpad/dist/``. The documented default could not be executed as
    documented unless every caller knew to add ``--workspace .``, which is
    precisely the knowledge a default exists to remove.

    The ``agent-<hash>`` worktree case is kept rather than deleted, because a
    ``.claude/worktrees/agent-*`` checkout of the SITE-ONLY tree really does
    sit two levels below the data workspace and really has no ``dist/`` of its
    own. It is now conditioned on that being true instead of assumed from the
    directory name, so a worktree of the CONSOLIDATED tree -- which carries
    its own tracked ``dist/review/MANIFEST.csv`` -- correctly uses itself.
    """
    if REPO.name.startswith("agent-") and not (REPO / WORKSPACE_MARKER).exists():
        return REPO.parents[2]
    return REPO


DEFAULT_WORKSPACE = _default_workspace()

#: The storefront's twelve, by product id, in shelf-then-catalog order. The
#: shelf placement is Cedar's own (``shelf`` in the descriptors); this tuple
#: only fixes the order the shelf renders in and which ids ship.
STOREFRONT: tuple[str, ...] = (
    "funding",
    "federal-register",
    "legislation",
    "deals",
    "nagpra",
    "lobbying",
    "contractors",
    "subcontracting",
    "owned",
    "need",
    "natural-resources",
    "nonprofits",
    "foundation-corporate-giving",
    "plot",
)

#: Measured by Cedar, deliberately not on the storefront. Kept by name and
#: reason so a reader can see what was left out and why, and so removing one
#: is a decision somebody made rather than an absence nobody noticed.
EXCLUDED: dict[str, str] = {
    "newsletters": (
        "Owner ruling, 2026-09-02: not a Cedar Press product. The collection "
        "and its data remain in the Cedar workspace; only the storefront slot "
        "is withdrawn."
    ),
    "gaming": (
        "Shelf 'grove': Gaming Intelligence is built for Cedar Grove and is "
        "still in progress. Cedar Press neither sells nor previews it; it "
        "returns to the storefront's catalog when the workspace rules it ready."
    ),
    "_entity_layer": (
        "Shelf 'infrastructure': the identity spine every other collection "
        "keys to, not a collection sold on its own."
    ),
    "infrastructure": (
        "A separate Cedar Grove dataset. Records retain source-specific periods, "
        "grains and publication permissions."
    ),
}

#: The fourteen fields ``CollectionDataset`` declares. 760 emits exactly these
#: and nothing else; this checks it in both directions rather than trusting it,
#: because that contract has broken twice on this interface before.
DESCRIPTOR_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "short_name",
        "origin",
        "level",
        "tracks",
        "rows_label",
        "downloads",
        "vintage",
        "version",
        "updated",
        "sources",
        "method",
        "shelf",
    }
)

#: Fields Cedar publishes with no measurement behind them. Written ``null``
#: and reported, never filled.
UNMEASURED: dict[str, str] = {
    "vintage": (
        "760 emits an empty vintage for every collection: the cadence "
        "measurement it derives the newest held period from produced nothing "
        "for any of the fifteen. No period is stated rather than a plausible "
        "one being chosen."
    ),
    "downloads": (
        "A platform metric, not a Cedar measurement. 760: 'It lives in the "
        "platform database and Cedar has no business inventing it.' No "
        "download counter exists yet, so the count is absent, not zero."
    ),
}


def _flagship_map(workspace: Path) -> dict[str, str]:
    """``770_sample_extracts.FLAGSHIP`` read out by text.

    The one table a customer opens first is a curated choice the data project
    already made and documents. Reading it out of the source rather than
    retyping it here means a rename there surfaces as a missing key rather
    than as this repo quietly shipping the wrong table -- which is how 760
    reads the same dict, for the same reason.
    """
    source = workspace / "code" / "770_sample_extracts.py"
    text = source.read_text(encoding="utf-8", errors="replace")
    start = text.find("FLAGSHIP = {")
    if start == -1:
        raise SystemExit(
            f"{source}: no FLAGSHIP dict -- refusing to guess a flagship table"
        )
    body = text[start + len("FLAGSHIP = {") : text.find("\n}", start)]
    found = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body))
    if not found:
        raise SystemExit(
            f"{source}: FLAGSHIP parsed empty -- refusing to guess a flagship table"
        )
    return found


def _require(path: Path, produced_by: str) -> Path:
    if not path.exists():
        raise SystemExit(f"missing input: {path}\n  produce it with: {produced_by}")
    return path


def build(workspace: Path) -> dict:
    dist = workspace / "dist"
    descriptors_path = _require(
        dist / "collection_descriptors.json", "py -3 code/760_collection_descriptors.py"
    )
    cedar_path = _require(
        dist / "collection_descriptors.cedar.json",
        "py -3 code/760_collection_descriptors.py",
    )
    review_path = _require(
        dist / "review" / "MANIFEST.csv",
        "py -3 code/1135_full_dataset_review_bundle.py samples",
    )

    descriptors = {
        d["id"]: d for d in json.loads(descriptors_path.read_text(encoding="utf-8"))
    }
    cedar = json.loads(cedar_path.read_text(encoding="utf-8"))
    flagship = _flagship_map(workspace)

    for did, descriptor in descriptors.items():
        extra = set(descriptor) - DESCRIPTOR_FIELDS
        missing = DESCRIPTOR_FIELDS - set(descriptor)
        if extra or missing:
            raise SystemExit(
                f"{did}: descriptor does not carry exactly the CollectionDataset fields "
                f"(unsupported: {sorted(extra)}; missing: {sorted(missing)})"
            )

    # Review rows are keyed by CEDAR id; the product id differs for `owned`.
    product_of = {facts["cedar_id"]: pid for pid, facts in cedar.items()}
    tables_by_product: dict[str, list[dict]] = {}
    with review_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pid = product_of.get(row["collection"], row["collection"])
            tables_by_product.setdefault(pid, []).append(row)

    unknown = [cid for cid in STOREFRONT if cid not in descriptors]
    if unknown:
        raise SystemExit(f"storefront ids Cedar does not measure: {unknown}")
    unplaced = sorted(set(descriptors) - set(STOREFRONT) - set(EXCLUDED))
    if unplaced:
        raise SystemExit(
            f"Cedar measures collections this script neither ships nor excludes: {unplaced}. "
            "Add each to STOREFRONT or to EXCLUDED with a reason."
        )

    collections = []
    for cid in STOREFRONT:
        descriptor = dict(descriptors[cid])
        facts = cedar[cid]
        cedar_id = facts["cedar_id"]

        # Absent, not zero, and absent, not "": see UNMEASURED.
        descriptor["vintage"] = descriptor["vintage"] or None
        descriptor["downloads"] = None

        rows = tables_by_product.get(cid, [])
        tables = [
            {
                "table": row["table"],
                "sample_path": f"/data/cedar/samples/{cedar_id}/"
                f"{Path(row['table']).stem}__10.csv",
                "rows_in": _int(row["rows_in"]),
                "rows_published": _int(row["rows_published"]),
                "rows_withheld": _int(row["rows_withheld"]),
                "withheld_why": row["withheld_why"] or None,
                "columns_published": _int(row["columns_published"]),
                "sample_rows": _int(row["sample_rows"]),
                # How the full table is delivered when a serving layer exists.
                "full_file": {
                    "shippable": row["shippable"] == "1",
                    "split": row["split"],
                    "files": _int(row["files"]),
                    "largest_file_mb": _float(row["largest_file_mb"]),
                },
            }
            for row in sorted(rows, key=lambda r: r["table"])
        ]

        flagship_table = flagship.get(cedar_id)
        if flagship_table is None:
            raise SystemExit(
                f"{cid}: 770 names no flagship table -- refusing to pick one"
            )
        sample = next((t for t in tables if t["table"] == flagship_table), None)
        if sample is None:
            # `owned` is the live case and the reason this is a branch rather
            # than a raise. 770's flagship for it is `native_owned_businesses.csv`
            # (2,916 rows) and no collection contract claims that table, so 1135
            # never built it and 760 withdrew the row count and marked the
            # dataset BLOCKED for exactly this. A READY collection missing its
            # flagship is still a build failure; a BLOCKED one carries the
            # absence as data, because substituting a different table here
            # would resolve by choice a disagreement Cedar has not resolved.
            if not facts["blockers"]:
                raise SystemExit(
                    f"{cid}: READY, but flagship {flagship_table} has no row in the "
                    "review manifest"
                )
            sample_entry = {
                "table": None,
                "path": None,
                "unavailable_because": (
                    f"770 names {flagship_table} as this collection's flagship table and "
                    "no collection contract claims it, so 1135 built no sample for it and "
                    "760 withdrew the dataset's row count. The tables the contract does "
                    "claim are listed below with their own samples; none of them is the "
                    "table a customer would open first."
                ),
            }
        else:
            sample_entry = {
                "table": flagship_table,
                "path": sample["sample_path"],
                "rows": sample["sample_rows"],
                "of": sample["rows_in"],
                "columns": sample["columns_published"],
            }

        collections.append(
            {
                "id": cid,
                # Exactly the fourteen, so `CollectionDataset(**descriptor)`
                # loads it. Everything Cedar knows that the product's dataclass
                # does not declare lives beside it, never inside it.
                "descriptor": descriptor,
                "cedar": {
                    "cedar_id": cedar_id,
                    "status": facts["status"],
                    "blockers": list(facts["blockers"]),
                    "n_rows": facts["n_rows"],
                    "n_tables": facts["n_tables"],
                },
                "sample": sample_entry,
                "tables": tables,
                "full_files": {
                    "served": False,
                    "note": (
                        "The full spreadsheets are built by "
                        "code/1135_full_dataset_review_bundle.py and are not in this "
                        "repository: the set measures 6.2 GB and single tables exceed "
                        "GitHub's 100 MB limit. Each table above carries the split and "
                        "file count a serving layer needs to locate it."
                    ),
                },
            }
        )

    return {
        "provenance": {
            "generator": "scripts/import_cedar_manifest.py",
            "workspace_inputs": {
                "descriptors": "dist/collection_descriptors.json (code/760_collection_descriptors.py)",
                "cedar_facts": "dist/collection_descriptors.cedar.json (same script)",
                "review_manifest": "dist/review/MANIFEST.csv (code/1135_full_dataset_review_bundle.py)",
                "samples": "dist/review/samples/<collection>/<table>__10.csv (same script)",
                "flagship_tables": "code/770_sample_extracts.py FLAGSHIP, read by text",
            },
            "note": (
                "Every value in this file is copied from those inputs. Nothing is "
                "typed here, and a field Cedar does not measure is null and named "
                "in unmeasured_fields."
            ),
        },
        "unmeasured_fields": UNMEASURED,
        "excluded": [
            {"id": cid, "shelf": descriptors[cid]["shelf"], "reason": reason}
            for cid, reason in EXCLUDED.items()
            if cid in descriptors
        ],
        "collections": collections,
    }


def _int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


#: The publication rule itself, from the workspace's own module: the withheld
#: class, the per-field lists and the predicate. Loaded by path so this script
#: cannot drift from the rule it enforces; if the module is missing the
#: importer refuses rather than guessing (fail closed).
def _publication_rule(module_name="cedar_domain"):
    import importlib.util

    source = REPO / "code" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise SystemExit(
            f"publication rule not found at {source}; refusing to import samples"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RULE = _publication_rule()
_COLLECTION_RULE = _publication_rule("cedar_publication")
WITHHELD_CLASS = _RULE.INDIVIDUAL_NATIVE_CLASS
WITHHELD_FIELDS = frozenset(_RULE.INDIVIDUAL_NATIVE_WITHHELD_FIELDS)
may_publish_individual_native_field = _RULE.may_publish_individual_native_field

WITHHELD_WHY = (
    "The sample carries a field the publication rule withholds for an individually "
    "Native-owned firm (may_publish_individual_native_field), "
    "so the file is not published. The table is still in the release."
)
# Owner ruling 2026-10-02: a firm is a business entity regardless of what it
# is named after, and its name, identifiers and business address are public
# business records, so may_publish_individual_native_field now publishes every
# field it used to withhold absent consent. The gate below is unchanged in
# shape and asks the rule for every cell, so it strikes nothing for those
# fields now and would strike again if the rule ever withheld one. The name
# backstop asks the rule for `canonical_name` rather than reading consent.


def withheld_entities(spine_names: Path) -> tuple[frozenset[str], frozenset[str]]:
    """The withheld class in the register: (names lowercased and trimmed, uids)."""
    names: set[str] = set()
    uids: set[str] = set()
    with spine_names.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["entity_class"] != WITHHELD_CLASS:
                continue
            uids.add(row["cedar_uid"].strip())
            if row["name"].strip():
                names.add(row["name"].strip().lower())
    return frozenset(names), frozenset(uids)


def withheld_names(spine_names: Path) -> frozenset[str]:
    return withheld_entities(spine_names)[0]


def sample_violations(
    sample: Path, names: frozenset[str], uids: frozenset[str]
) -> list[str]:
    """The columns of a sample that publish what the rule withholds.

    Field-level, the way the rule is written (Codex, PR #63): a row is an
    individual-business row when any cell is one of the class's uids or
    names or its ``entity_class`` is the class; on such a row every non-empty
    column in the rule's field list is a violation unless
    ``may_publish_individual_native_field`` releases it for that row's
    ``consent_status`` and ``firm_legal_name_is_person``. A cell equal to a
    class name under ANY column is a violation as well (the backstop for a
    name carried under a header the list does not know) unless the rule
    releases ``canonical_name`` for that row. Since the owner ruling of
    2026-10-02 the rule releases every such field, so nothing is struck; the
    machinery stays so a future withholding is enforced here again.
    """
    hit: list[str] = []
    with sample.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cells = {
                column: (value or "").strip() for column, value in row.items() if column
            }
            individual = (
                cells.get("entity_class") == WITHHELD_CLASS
                or any(value in uids for value in cells.values())
                or any(value.lower() in names for value in cells.values())
            )
            if not individual:
                continue
            consent = cells.get("consent_status", "NOT_ASKED")
            person = cells.get("firm_legal_name_is_person")
            for column, value in cells.items():
                if not value:
                    continue
                withheld_field = (
                    column in WITHHELD_FIELDS
                    and not may_publish_individual_native_field(
                        column, name_is_person=person, consent_status=consent
                    )
                )
                named = value.lower() in names and not may_publish_individual_native_field(
                    "canonical_name", name_is_person=person, consent_status=consent
                )
                if (withheld_field or named) and column not in hit:
                    hit.append(column)
    return hit


def sample_carries_withheld_name(sample: Path, names: frozenset[str]) -> list[str]:
    """The name backstop alone; kept for callers that have no uid list."""
    return sample_violations(sample, names, frozenset())


def review_sample(workspace: Path):
    """Where the importer reads a table's sample: the review bundle's layout."""

    def locate(collection: dict, table: dict) -> Path:
        cedar_id = collection["cedar"]["cedar_id"]
        return review_sample_path(workspace, cedar_id, table["table"])

    return locate


def review_sample_path(workspace: Path, cedar_id: str, table: str) -> Path:
    """Read only a declared review sample inside the supplied review bundle."""
    if not cedar_id or cedar_id in (".", "..") or any(c in cedar_id for c in "/\\:"):
        raise ValueError("Invalid sample collection identifier")
    root = (workspace / "dist" / "review" / "samples").resolve()
    source = (root / cedar_id / f"{Path(table).stem}__10.csv").resolve()
    if not source.is_relative_to(root):
        raise ValueError("Sample source escapes review bundle")
    return source


def public_sample_path(repo: Path, url: str) -> Path:
    """Resolve a local asset URL inside public; refuse traversal and external links."""
    if not isinstance(url, str) or not url.startswith("/") or url.startswith("//"):
        raise ValueError("Sample must use a local public URL")
    if "\\" in url or ":" in url or "?" in url or "#" in url or "%" in url:
        raise ValueError("Invalid public sample URL")
    relative = Path(url[1:])
    if ".." in relative.parts:
        raise ValueError("Public sample path traversal")
    repository = repo.resolve()
    root = (repository / "public").resolve()
    if not root.is_relative_to(repository):
        raise ValueError("Public directory escapes repository")
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError("Sample path escapes public directory")
    return target


def public_sample(repo: Path):
    """Where the site serves a table's sample: the manifest's own path under public/."""

    def locate(collection: dict, table: dict) -> Path:
        return public_sample_path(repo, table["sample_path"])

    return locate


def withhold_samples(
    manifest: dict,
    locate,
    names: frozenset[str],
    uids: frozenset[str] = frozenset(),
    *,
    repo: Path = REPO,
) -> list[dict]:
    """Strike every declared sample that publishes what the rule withholds.

    ``locate(collection, table)`` says where the file is: the review bundle's
    layout on an import, ``public/`` on an audit (Codex, PR #63: the manifest
    path is a URL, not the bundle's layout, and joining it to the bundle found
    nothing and struck nothing). Applied to the manifest in place: the table
    keeps its row counts and its release facts and loses its ``sample_path``,
    gaining ``sample_withheld_why`` and the offending columns; a flagship so
    struck leaves the collection's ``sample`` entry with the reason. Returns
    what was struck, with the served path, so the caller deletes the file
    an earlier import may have published. Pure over its inputs, so the tests
    can plant a sample and prove the strike.
    """
    struck: list[dict] = []
    for collection in manifest["collections"]:
        flagship = collection.get("sample") or {}
        need_tables = set()
        if collection.get("id") == "need":
            from cedar_press.need_preview import need_preview_permitted

            need_tables = {
                (table.get("table"), table["sample_path"])
                for table in collection["tables"]
                if table.get("sample_path")
                and need_preview_permitted(
                    repo, collection, table, lambda: locate(collection, table)
                )
            }
        policy_hold = None
        try:
            _COLLECTION_RULE.assert_collection_publishable(
                collection.get("cedar", {}).get("cedar_id", collection["id"])
            )
        except _COLLECTION_RULE.FieldMapRefusal:
            if need_tables:
                collection.pop("publication_hold", None)
                collection["publication_scope"] = "reviewed_public_base_only"
            else:
                policy_hold = "This collection is withheld from publication under its maintained publication policy."
                collection["publication_hold"] = {
                    "code": "COLLECTION_PUBLICATION_HOLD",
                    "message": policy_hold,
                }
                collection.setdefault("cedar", {})["status"] = "BLOCKED"
                collection["cedar"]["blockers"] = [policy_hold]
        for table in collection["tables"]:
            path = table.get("sample_path")
            if not path:
                continue
            table_hold = policy_hold
            if (
                collection.get("id") == "need"
                and (table.get("table"), path) not in need_tables
            ):
                table_hold = "Only the exact evidence-pinned reviewed NEED base preview is public."
            if table_hold:
                columns = ["all fields: collection publication hold"]
            else:
                file = locate(collection, table)
                if not file.exists():
                    continue
                columns = sample_violations(file, names, uids)
                if not columns:
                    continue
            table["sample_path"] = None
            table["sample_withheld_path"] = path
            table["sample_withheld_why"] = table_hold or WITHHELD_WHY
            table["sample_withheld_columns"] = columns
            struck.append(
                {
                    "collection": collection["id"],
                    "table": table["table"],
                    "path": path,
                    "columns": columns,
                }
            )
            if flagship.get("path") == path:
                collection["sample"] = {
                    "table": flagship.get("table"),
                    "path": None,
                    "unavailable_because": table_hold or WITHHELD_WHY,
                }
    return struck


def unpublish(repo: Path, struck: list[dict]) -> None:
    """Delete the served copy of every struck sample, if an earlier import published one."""
    paths = [public_sample_path(repo, entry["path"]) for entry in struck]
    for served in paths:
        if served.exists():
            served.unlink()


def audit(repo: Path = REPO) -> list[dict]:
    """Apply the withholding rule to the committed manifest and public/ files.

    ``python scripts/import_cedar_manifest.py --audit``. Rewrites the manifest,
    deletes each struck file under public/, removes local filesystem paths
    from the samples still served (``scrub_local_paths``), and prints what it
    struck and what it scrubbed. The
    caller re-runs measure-samples and derive-explore (the test suites name
    both when stale).
    """
    manifest_path = repo / "data" / "cedar" / "collections.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    original = json.dumps(manifest, sort_keys=True)
    names, uids = withheld_entities(repo / "data" / "spine" / "cedar_entity_names.csv")
    struck = withhold_samples(manifest, public_sample(repo), names, uids, repo=repo)
    unpublish(repo, struck)
    for sample in scrub_public_samples(repo):
        print(f"  scrubbed  local path(s) from {sample.relative_to(repo)}")
    if json.dumps(manifest, sort_keys=True) != original:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return struck


#: A path on somebody's machine: a home directory, POSIX or Windows. Never
#: inside a URL (the lookbehind refuses a path glued to a host or another
#: path segment), and ``~`` only as ``~/``, so "~20%" is not a path.
LOCAL_PATH = re.compile(
    r"(?<![\w.:/\\-])"
    r"(?:~(?=/)|/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)"
    r"(?:[/\\][^\s)\"',;|]*)?"
)
#: The clause the NEED builder wrote around the path (code/1133 ``OWNER_DOC``):
#: dropped whole, so the parenthetical keeps its description and loses the
#: machine it was on.
ON_THIS_MACHINE = re.compile(r",?\s*on this machine at\s+" + LOCAL_PATH.pattern)
#: A replacement for what is left of a path the clause above did not cover.
LOCAL_PATH_REMOVED = "[local path removed]"


def scrub_local_paths(text: str) -> str:
    """A published sample's text with every local filesystem path removed.

    FOUND 2026-09-27: ``need_enterprises__10.csv`` published, in
    ``source_document``, "the owner's research dataset, on this machine at
    ~/Desktop/dissertation/data/tribal_federal_spending/clean/" -- a path on
    the owner's own computer, served to every visitor of the site. The value
    is written upstream (code/1133) and reaches the site through this copy,
    so this copy is where a public file stops carrying it, for that value and
    for any later one of the same shape. Applied to the raw text, not parsed
    cells: nothing substituted in carries a comma, a quote or a newline, so
    the file's own quoting is left byte for byte as 1135 wrote it.
    """
    text = ON_THIS_MACHINE.sub("", text)
    text = text.replace("the owner's research dataset", "Lumecon research dataset")
    return LOCAL_PATH.sub(LOCAL_PATH_REMOVED, text)


def publish_sample(source: Path, target: Path) -> bool:
    """Write ``source`` to ``target`` without local paths; True if any were removed."""
    raw = source.read_text(encoding="utf-8")
    clean = scrub_local_paths(raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    # newline="" so a CRLF in the source stays CRLF: the bytes are 1135's.
    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(clean)
    return clean != raw


def scrub_public_samples(repo: Path = REPO) -> list[Path]:
    """Rewrite every served sample under ``public/`` that carries a local path."""
    rewritten: list[Path] = []
    root = repo / "public" / "data" / "cedar" / "samples"
    for sample in sorted(root.rglob("*.csv")):
        raw = sample.read_text(encoding="utf-8")
        if scrub_local_paths(raw) != raw:
            publish_sample(sample, sample)
            rewritten.append(sample)
    return rewritten


def copy_samples(workspace: Path, manifest: dict) -> int:
    """The ten-row samples the manifest points at, and nothing else.

    Copied under ``public/`` so the built site serves them at the same URL the
    manifest states, and so the Python side and the browser read one set of
    bytes rather than two copies that can disagree -- bar one deliberate
    difference: a local filesystem path in the review bundle never reaches the
    served copy (``scrub_local_paths``).
    """
    written = 0
    for collection in manifest["collections"]:
        cedar_id = collection["cedar"]["cedar_id"]
        try:
            _COLLECTION_RULE.assert_collection_publishable(cedar_id)
        except _COLLECTION_RULE.FieldMapRefusal:
            if any(table.get("sample_path") for table in collection["tables"]):
                raise ValueError(
                    "Stale manifest attempts to copy a publication-held collection"
                ) from None
            continue
        for table in collection["tables"]:
            if not table.get("sample_path"):
                continue  # struck by withhold_samples: never copied
            source = review_sample_path(workspace, cedar_id, table["table"])
            if not source.exists():
                raise SystemExit(f"missing sample: {source}")
            target = public_sample_path(REPO, table["sample_path"])
            if publish_sample(source, target):
                print(f"  scrubbed  local path(s) from {target.relative_to(REPO)}")
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument(
        "--audit",
        action="store_true",
        help="apply the publication rule to the committed manifest and public/ "
        "samples instead of importing; strikes and deletes what it withholds",
    )
    args = parser.parse_args()
    if args.audit:
        for entry in audit():
            print(f"  withheld  {entry['path']}  ({', '.join(entry['columns'])})")
        return 0
    workspace = args.workspace.resolve()

    manifest = build(workspace)
    # The publication rule, before a file becomes a public asset: a sample
    # that names an individually Native-owned firm without consent is struck
    # from the manifest here and never copied below.
    names, uids = withheld_entities(
        workspace / "data" / "spine" / "cedar_entity_names.csv"
    )
    struck = withhold_samples(manifest, review_sample(workspace), names, uids)
    # And the copy an earlier import may have published: skipping the new
    # copy alone would leave the old file served (Codex, PR #63).
    unpublish(REPO, struck)
    for entry in struck:
        print(f"  withheld  {entry['path']}  ({', '.join(entry['columns'])})")
    out = REPO / "data" / "cedar" / "collections.manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    written = copy_samples(workspace, manifest)
    # The record of which declared samples the repository holds follows every
    # import; the tests refuse a stale one. On the importer's machine every
    # sample was just copied, so the record says none is missing -- until the
    # files are committed elsewhere, which is exactly what it exists to show.
    measured = subprocess.run(
        ["node", str(REPO / "scripts" / "measure-samples.mjs")],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=120,
    )
    if measured.returncode != 0:
        raise SystemExit(f"measure-samples failed:\n{measured.stderr}")
    # The Explore card's per-table contracts are read off the sample headers
    # just copied, so they follow every import for the same reason.
    derived = subprocess.run(
        ["node", str(REPO / "scripts" / "derive-explore.mjs")],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=120,
    )
    if derived.returncode != 0:
        raise SystemExit(f"derive-explore failed:\n{derived.stderr}")

    print(f"  manifest  {out.relative_to(REPO)}")
    print(f"  storefront {len(manifest['collections'])} collections")
    print(f"  excluded   {', '.join(e['id'] for e in manifest['excluded'])}")
    print(f"  samples    {written} files copied under public/data/cedar/samples/")
    for collection in manifest["collections"]:
        cedar = collection["cedar"]
        flag = "BLOCKED" if cedar["blockers"] else "        "
        print(
            f"    {flag} {collection['id']:<20} {collection['descriptor']['shelf']:<9} "
            f"{collection['descriptor']['rows_label']:<22} {cedar['n_tables']:>3} tables"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
