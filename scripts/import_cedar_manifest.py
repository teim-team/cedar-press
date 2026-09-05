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
import shutil
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
    "nest",
    "natural-resources",
    "nonprofits",
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
        raise SystemExit(f"{source}: no FLAGSHIP dict -- refusing to guess a flagship table")
    body = text[start + len("FLAGSHIP = {") : text.find("\n}", start)]
    found = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body))
    if not found:
        raise SystemExit(f"{source}: FLAGSHIP parsed empty -- refusing to guess a flagship table")
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
        dist / "collection_descriptors.cedar.json", "py -3 code/760_collection_descriptors.py"
    )
    review_path = _require(
        dist / "review" / "MANIFEST.csv",
        "py -3 code/1135_full_dataset_review_bundle.py samples",
    )

    descriptors = {d["id"]: d for d in json.loads(descriptors_path.read_text(encoding="utf-8"))}
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
            raise SystemExit(f"{cid}: 770 names no flagship table -- refusing to pick one")
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
def _publication_rule():
    import importlib.util
    source = REPO / "code" / "cedar_domain.py"
    spec = importlib.util.spec_from_file_location("cedar_domain", source)
    if spec is None or spec.loader is None:
        raise SystemExit(f"publication rule not found at {source}; refusing to import samples")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RULE = _publication_rule()
WITHHELD_CLASS = _RULE.INDIVIDUAL_NATIVE_CLASS
WITHHELD_FIELDS = frozenset(_RULE.INDIVIDUAL_NATIVE_WITHHELD_FIELDS)
may_publish_individual_native_field = _RULE.may_publish_individual_native_field

WITHHELD_WHY = (
    "The sample carries a field the publication rule withholds for an individually "
    "Native-owned firm without recorded consent (may_publish_individual_native_field), "
    "so the file is not published. The table is still in the release."
)


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


def sample_violations(sample: Path, names: frozenset[str], uids: frozenset[str]) -> list[str]:
    """The columns of a sample that publish what the rule withholds.

    Field-level, the way the rule is written (Codex, PR #63): a row is an
    individual-business row when any cell is one of the class's uids or
    names or its ``entity_class`` is the class; on such a row every non-empty
    column in the withheld-field list is a violation unless
    ``may_publish_individual_native_field`` releases it for that row's
    ``consent_status`` and ``firm_legal_name_is_person``. A cell equal to a
    withheld name under ANY column is a violation as well (the backstop for a
    name carried under a header the list does not know), again unless the
    row records consent.
    """
    hit: list[str] = []
    with sample.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cells = {column: (value or "").strip() for column, value in row.items() if column}
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
                withheld_field = column in WITHHELD_FIELDS and not may_publish_individual_native_field(
                    column, name_is_person=person, consent_status=consent
                )
                named = value.lower() in names and consent.upper() != "OPTED_IN"
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
        return workspace / "dist" / "review" / "samples" / cedar_id / f"{Path(table['table']).stem}__10.csv"
    return locate


def public_sample(repo: Path):
    """Where the site serves a table's sample: the manifest's own path under public/."""
    def locate(collection: dict, table: dict) -> Path:
        return repo / "public" / table["sample_path"].lstrip("/")
    return locate


def withhold_samples(manifest: dict, locate, names: frozenset[str], uids: frozenset[str] = frozenset()) -> list[dict]:
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
        for table in collection["tables"]:
            path = table.get("sample_path")
            if not path:
                continue
            file = locate(collection, table)
            if not file.exists():
                continue
            columns = sample_violations(file, names, uids)
            if not columns:
                continue
            table["sample_path"] = None
            table["sample_withheld_why"] = WITHHELD_WHY
            table["sample_withheld_columns"] = columns
            struck.append({"collection": collection["id"], "table": table["table"],
                           "path": path, "columns": columns})
            if flagship.get("path") == path:
                collection["sample"] = {
                    "table": flagship.get("table"),
                    "path": None,
                    "unavailable_because": WITHHELD_WHY,
                }
    return struck


def unpublish(repo: Path, struck: list[dict]) -> None:
    """Delete the served copy of every struck sample, if an earlier import published one."""
    for entry in struck:
        served = repo / "public" / entry["path"].lstrip("/")
        if served.exists():
            served.unlink()


def audit(repo: Path = REPO) -> list[dict]:
    """Apply the withholding rule to the committed manifest and public/ files.

    ``python scripts/import_cedar_manifest.py --audit``. Rewrites the manifest,
    deletes each struck file under public/, and prints what it struck. The
    caller re-runs measure-samples and derive-explore (the test suites name
    both when stale).
    """
    manifest_path = repo / "data" / "cedar" / "collections.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names, uids = withheld_entities(repo / "data" / "spine" / "cedar_entity_names.csv")
    struck = withhold_samples(manifest, public_sample(repo), names, uids)
    unpublish(repo, struck)
    if struck:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return struck


def copy_samples(workspace: Path, manifest: dict) -> int:
    """The ten-row samples the manifest points at, and nothing else.

    Copied under ``public/`` so the built site serves them at the same URL the
    manifest states, and so the Python side and the browser read one set of
    bytes rather than two copies that can disagree.
    """
    source_root = workspace / "dist" / "review" / "samples"
    written = 0
    for collection in manifest["collections"]:
        cedar_id = collection["cedar"]["cedar_id"]
        for table in collection["tables"]:
            if not table.get("sample_path"):
                continue  # struck by withhold_samples: never copied
            name = f"{Path(table['table']).stem}__10.csv"
            source = source_root / cedar_id / name
            if not source.exists():
                raise SystemExit(f"missing sample: {source}")
            target = REPO / "public" / table["sample_path"].lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument(
        "--audit", action="store_true",
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
    names, uids = withheld_entities(workspace / "data" / "spine" / "cedar_entity_names.csv")
    struck = withhold_samples(manifest, review_sample(workspace), names, uids)
    # And the copy an earlier import may have published: skipping the new
    # copy alone would leave the old file served (Codex, PR #63).
    unpublish(REPO, struck)
    for entry in struck:
        print(f"  withheld  {entry['path']}  ({', '.join(entry['columns'])})")
    out = REPO / "data" / "cedar" / "collections.manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written = copy_samples(workspace, manifest)
    # The record of which declared samples the repository holds follows every
    # import; the tests refuse a stale one. On the importer's machine every
    # sample was just copied, so the record says none is missing -- until the
    # files are committed elsewhere, which is exactly what it exists to show.
    measured = subprocess.run(  # noqa: S603
        ["node", str(REPO / "scripts" / "measure-samples.mjs")],
        capture_output=True, text=True, check=False,
    )
    if measured.returncode != 0:
        raise SystemExit(f"measure-samples failed:\n{measured.stderr}")
    # The Explore card's per-table contracts are read off the sample headers
    # just copied, so they follow every import for the same reason.
    derived = subprocess.run(  # noqa: S603
        ["node", str(REPO / "scripts" / "derive-explore.mjs")],
        capture_output=True, text=True, check=False,
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
