"""The cross-language contract: Python and JavaScript hold one collection.

``server/cedar_press/collections.py`` said, from the day it was written:

    The two implementations must move together: this file mirrors the JS module
    value for value, and ``tests/test_collection.py`` holds the same contracts
    the JS suite holds, so a release that changes a series in one language and
    not the other fails a build instead of shipping two different collections.

There was no ``tests/test_collection.py``. Nothing anywhere compared the two,
and by the time anyone looked they had already drifted in two places: the
Python descriptor carried ``shelf`` and the JavaScript one did not, and the
JavaScript citation resolved its version through ``pressReleases.js`` while
Python read the descriptor, so ``deals`` cited as v9.0 in the browser and v9 on
the server. A docstring is not a check.

This is the check. It executes BOTH implementations -- Python in-process,
JavaScript through ``scripts/dump-collection.mjs`` -- and compares every value
the two produce. It lives here rather than at the path the docstring named
because ``tests/`` is Playwright's directory and CI runs the Python suite as
``python -m unittest discover -s tests -t .`` from ``server/``. A test at a
path nothing runs is the same defect as a docstring: a claim with no body.

Both sides read ``data/cedar/collections.manifest.json``, so the descriptors
cannot differ by construction. That is not a reason to skip comparing them --
it is the reason to compare everything else too, because the derived strings,
the figures, the findings, the citations and the download bytes are still two
bodies of code that can disagree while reading identical inputs.

If ``node`` is unavailable the test FAILS rather than skipping. A parity check
that quietly does not run is worse than no parity check, because the docstring
above is then true again in the only sense that matters.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import shutil
import subprocess
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cedar_press import collection_profiles, press_catalog
from cedar_press import collections as launch

_REPO = Path(__file__).resolve().parents[2]
_DUMP = _REPO / "scripts" / "dump-collection.mjs"
_PRESS_DUMP = _REPO / "scripts" / "dump-press.mjs"

#: The same fixed date the JavaScript dump uses. Neither implementation reads a
#: clock, so this comparison cannot flap at midnight.
ACCESSED = "1 January 2026"


def _run(script: Path) -> dict:
    """Run one of the dump scripts and read back everything it produces."""
    node = shutil.which("node")
    if node is None:
        raise AssertionError("node is not on PATH")
    result = subprocess.run(  # noqa: S603
        [node, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=_REPO,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{script.name} exited {result.returncode}:\n{result.stderr}"
        )
    return json.loads(result.stdout)


def _javascript() -> dict:
    """The launch collection, as the JavaScript implementation produces it."""
    return _run(_DUMP)


def _javascript_press() -> dict:
    """The Press ladder, as ``pressCatalog.js`` and its siblings produce it."""
    return _run(_PRESS_DUMP)


class TestCrossLanguageParity(unittest.TestCase):
    """Every value both implementations produce, compared."""

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise AssertionError(
                "node is not on PATH, so the two implementations cannot be compared. "
                "This fails rather than skips: an unrun parity check is how the two "
                "drifted the first time."
            )
        cls.js = _javascript()

    # -- descriptors ----------------------------------------------------

    def test_the_same_collections_in_the_same_order(self) -> None:
        self.assertEqual(
            [d.id for d in launch.LAUNCH_COLLECTION],
            [d["id"] for d in self.js["launchCollection"]],
        )

    def test_every_descriptor_field_matches(self) -> None:
        # snake_case here, camelCase there, which is the one transformation the
        # JavaScript module performs and therefore the one this has to undo.
        rename = {"short_name": "shortName", "rows_label": "rowsLabel"}
        for python, javascript in zip(
            launch.LAUNCH_COLLECTION, self.js["launchCollection"], strict=True
        ):
            for field in dataclasses.fields(python):
                key = rename.get(field.name, field.name)
                with self.subTest(dataset=python.id, field=field.name):
                    self.assertIn(key, javascript)
                    self.assertEqual(getattr(python, field.name), javascript[key])

    def test_no_descriptor_field_exists_on_only_one_side(self) -> None:
        rename = {"short_name": "shortName", "rows_label": "rowsLabel"}
        expected = {
            rename.get(f.name, f.name)
            for f in dataclasses.fields(launch.CollectionDataset)
        }
        for javascript in self.js["launchCollection"]:
            with self.subTest(dataset=javascript["id"]):
                self.assertEqual(set(javascript), expected)

    def test_the_twelve_are_the_storefront(self) -> None:
        # The count is a product decision (owner ruling, 2026-09-02) and is
        # pinned so a thirteenth cannot arrive without somebody deciding to.
        self.assertEqual(len(launch.LAUNCH_COLLECTION), 12)
        self.assertEqual(
            {d.id for d in launch.LAUNCH_COLLECTION},
            {
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
            },
        )

    def test_newsletters_is_excluded_by_name_and_not_merely_absent(self) -> None:
        # Flag, never delete. The collection stays in Cedar and its sample rows
        # stay in this repository; what the ruling removed is the storefront
        # slot, and an exclusion nobody can see is one nobody can question.
        excluded = {entry["id"]: entry for entry in launch.EXCLUDED_COLLECTIONS}
        self.assertIn("newsletters", excluded)
        self.assertTrue(excluded["newsletters"]["reason"])
        self.assertNotIn("newsletters", {d.id for d in launch.LAUNCH_COLLECTION})
        self.assertEqual(
            [dict(e) for e in launch.EXCLUDED_COLLECTIONS], self.js["excluded"]
        )

    # -- honesty about what is not measured ------------------------------

    def test_unmeasured_fields_agree_and_are_actually_absent(self) -> None:
        self.assertEqual(launch.UNMEASURED_FIELDS, self.js["unmeasuredFields"])
        self.assertEqual(set(launch.UNMEASURED_FIELDS), {"vintage", "downloads"})
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                # None, not "" and not 0. An empty string reads as a vintage
                # nobody typed and a zero reads as a download count somebody
                # measured; both are the defect this pair of fields carries.
                self.assertIsNone(dataset.vintage)
                self.assertIsNone(dataset.downloads)

    def test_every_figure_declares_whether_it_is_a_measurement(self) -> None:
        for python, javascript in zip(
            launch.COLLECTION_FIGURES, self.js["figures"], strict=True
        ):
            with self.subTest(figure=python.id):
                self.assertIsInstance(python.demonstration, bool)
                self.assertEqual(python.demonstration, javascript["demonstration"])
        # Three of the four are placeholders and one is the nation-supplied
        # roster. If that ever becomes "all real" it should be because figures
        # arrived, not because a flag was flipped.
        by_id = {f.id: f.demonstration for f in launch.COLLECTION_FIGURES}
        self.assertFalse(by_id["owned"])
        self.assertTrue(all(v for k, v in by_id.items() if k != "owned"))

    def test_every_supported_finding_is_marked_demonstration(self) -> None:
        # None of these rests on a measurement: they read on the figure series,
        # and Cedar publishes none. The flag is in the data so a renderer can
        # see it without reading a comment.
        for finding in launch.collection_findings().supported:
            with self.subTest(finding=finding.id):
                self.assertTrue(finding.demonstration)

    def test_no_finding_or_figure_names_a_version_no_dataset_carries(self) -> None:
        # The basis strings used to say "Contractors v6" and "Deals v9", which
        # no release ever shipped. They are derived now; this pins that.
        live = {d.version for d in launch.LAUNCH_COLLECTION}
        stale = {"v4", "v6", "v9", "v0.1", "v4.2", "v9.0"} - live
        texts = [f.basis for f in launch.COLLECTION_FIGURES] + [
            f.basis for f in launch.collection_findings().supported
        ]
        for text in texts:
            for version in stale:
                with self.subTest(text=text, version=version):
                    self.assertNotIn(f" {version}", text)

    # -- derived values ---------------------------------------------------

    def test_the_context_line_matches(self) -> None:
        self.assertEqual(launch.collection_context_line(), self.js["contextLine"])

    def test_the_figures_match(self) -> None:
        self.assertEqual(
            [_listify_points(dataclasses.asdict(f)) for f in launch.COLLECTION_FIGURES],
            [_normalise_figure(f) for f in self.js["figures"]],
        )

    def test_the_figure_order_matches(self) -> None:
        self.assertEqual(
            [f.id for f in launch.figures_in_shelf_order()], self.js["figureOrder"]
        )

    def test_the_findings_match(self) -> None:
        findings = launch.collection_findings()
        js = self.js["findings"]
        self.assertEqual(
            [_camel(dataclasses.asdict(f)) for f in findings.supported], js["supported"]
        )
        self.assertEqual([dataclasses.asdict(n) for n in findings.needs], js["needs"])
        self.assertEqual(
            [_listify(dataclasses.asdict(n)) for n in findings.narratives],
            js["narratives"],
        )

    def test_the_citations_match(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                self.assertEqual(
                    launch.collection_citation(dataset.id, ACCESSED),
                    self.js["citations"][dataset.id],
                )
                self.assertEqual(
                    launch.collection_citation(dataset.id),
                    self.js["citationsWithoutDate"][dataset.id],
                )

    def test_an_unknown_id_is_none_on_both_sides(self) -> None:
        self.assertIsNone(launch.collection_citation("not-a-collection"))
        self.assertIsNone(self.js["unknownIdCitation"])

    def test_no_citation_prints_an_empty_vintage(self) -> None:
        # No collection states a vintage, and "vintage None" or "vintage ,"
        # in a citation is a reference nobody can check.
        for dataset in launch.LAUNCH_COLLECTION:
            citation = launch.collection_citation(dataset.id, ACCESSED)
            with self.subTest(dataset=dataset.id):
                self.assertNotIn("vintage", citation)
                self.assertNotIn("None", citation)

    # -- the manifest the downloads rest on --------------------------------

    def test_the_cedar_facts_match(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                self.assertEqual(
                    launch.collection_cedar_facts(dataset.id),
                    self.js["cedarFacts"][dataset.id],
                )

    def test_the_samples_and_tables_match(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                self.assertEqual(
                    launch.collection_sample(dataset.id), self.js["samples"][dataset.id]
                )
                self.assertEqual(
                    list(launch.collection_tables(dataset.id)),
                    self.js["tables"][dataset.id],
                )

    def test_every_declared_sample_file_exists_and_is_the_declared_shape(self) -> None:
        import csv as csv_module

        for dataset in launch.LAUNCH_COLLECTION:
            sample = launch.collection_sample(dataset.id)
            if not sample.get("path"):
                continue
            path = _REPO / "public" / sample["path"].lstrip("/")
            with self.subTest(dataset=dataset.id):
                self.assertTrue(path.exists(), f"{path} is declared and missing")
                with path.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv_module.reader(handle))
                # Parsed, not line-counted: `subcontracting`'s sample carries a
                # newline inside a quoted cell.
                self.assertEqual(len(rows) - 1, sample["rows"])
                self.assertEqual(len(rows[0]), sample["columns"])

    def test_every_table_the_manifest_names_has_its_sample_on_disk(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            for table in launch.collection_tables(dataset.id):
                if not table.get("sample_path"):
                    # Declared by the manifest, absent from the repository, and
                    # RECORDED as such by scripts/measure-samples.mjs: the site
                    # says so instead of linking to a 404. An absence with no
                    # record is the failure below.
                    with self.subTest(dataset=dataset.id, table=table["table"]):
                        self.assertTrue(table.get("sample_unpublished"),
                                        f"{table['table']} has no sample and no record")
                    continue
                path = _REPO / "public" / table["sample_path"].lstrip("/")
                # In the INDEX, not merely on this disk. `.gitignore` drops
                # every `*.csv` by extension, so a sample the importer wrote
                # and nobody force-added passes on the importer's machine
                # and fails everywhere else: 2026-09-05, twenty samples,
                # three red deploys. The rule now re-includes the samples
                # directory; this holds the line either way.
                with self.subTest(dataset=dataset.id, table=table["table"]):
                    self.assertTrue(path.exists(), f"{path} is declared and missing")
                    tracked = subprocess.run(  # noqa: S603
                        ["git", "-C", str(_REPO), "ls-files", "--error-unmatch",
                         str(path.relative_to(_REPO))],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(
                        tracked.returncode, 0,
                        f"{dataset.id}: {path.relative_to(_REPO)} is not tracked; "
                        "`git add` it from the checkout that ran the importer",
                    )

    def test_no_full_dataset_file_is_committed_to_this_repository(self) -> None:
        # 1135 also writes the full spreadsheets: 6.2 GB, with single tables
        # over GitHub's 100 MB limit. They are referenced by manifest entry and
        # must never arrive here by accident.
        oversized = [
            str(path.relative_to(_REPO))
            for path in (_REPO / "public" / "data" / "cedar").rglob("*")
            if path.is_file() and path.stat().st_size > 1_000_000
        ]
        self.assertEqual(oversized, [], "a file this large under samples/ is not a sample")
        # And a table's full file is described, never served from here.
        for dataset in launch.LAUNCH_COLLECTION:
            for table in launch.collection_tables(dataset.id):
                with self.subTest(dataset=dataset.id, table=table["table"]):
                    self.assertIn("split", table["full_file"])
                    self.assertIn("files", table["full_file"])

    def test_every_collection_has_a_sample_and_a_blocked_one_says_why(self) -> None:
        """UPDATED 2026-09-04. `owned` used to be the one collection with no
        sample, and this asserted that by name. The rebuild gave it one -
        native_owned_businesses__10.csv, 10 rows of 4,273 - so every collection
        now carries a sample and the old assertion read a fix as a regression.

        The invariant that actually matters survives and is asserted both ways:
        a collection either HAS a sample, or SAYS why it does not. Naming which
        collection is in which state was the brittle part.
        """
        without = [
            d.id
            for d in launch.LAUNCH_COLLECTION
            if not (launch.collection_sample(d.id) or {}).get("path")
        ]
        for cid in without:
            self.assertTrue(launch.sample_unavailable_reason(cid),
                            f"{cid} has no sample and no reason for it")
        # `owned` was BLOCKED with three named blockers at v0 and is READY with
        # none at v1 - the rebuild settled its membership and grain. Pinning the
        # test to BLOCKED would have made that fix look like a failure.
        #
        # The invariant is what gets asserted: a BLOCKED collection NAMES its
        # blockers rather than shipping the bare word, and a READY one has none.
        # That holds whichever state a collection is in.
        for dataset in launch.LAUNCH_COLLECTION:
            facts = launch.collection_cedar_facts(dataset.id)
            if facts["status"] == "BLOCKED":
                self.assertTrue(facts["blockers"],
                                f"{dataset.id} is BLOCKED and names no blocker")
            elif facts["status"] == "READY":
                self.assertFalse(facts["blockers"],
                                 f"{dataset.id} is READY and still lists blockers")

    # -- the bytes a reader receives ---------------------------------------

    def test_the_download_bytes_match(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                self.assertEqual(
                    launch.collection_csv(dataset.id), self.js["csvs"][dataset.id]
                )

    def test_every_download_carries_its_citation_last(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            csv_text = launch.collection_csv(dataset.id)
            if csv_text is None:
                continue
            with self.subTest(dataset=dataset.id):
                self.assertTrue(csv_text.split("\n")[-1].startswith("cite_as,"))


class TestPressCatalogSnapshot(unittest.TestCase):
    """The other cross-language pair: ``pressCatalog.js`` and ``CATALOG``.

    Python does not re-implement the Press ladder; it reads a snapshot,
    ``server/cedar_press/_press_data.json``, that ``scripts/dump-press.mjs``
    writes from the JavaScript modules. That is a weaker coupling than the
    launch collection's shared manifest and it fails in a quieter way: the
    JavaScript changes, nobody re-runs the dump, and the API serves last
    week's ladder while the browser renders this week's. Nothing checked it.

    This does. It re-runs the dump and compares it to the committed snapshot,
    so a stale ``_press_data.json`` fails a build instead of shipping.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise AssertionError(
                "node is not on PATH, so the Press catalogue cannot be compared "
                "against its snapshot. This fails rather than skips."
            )
        cls.js = _javascript_press()

    def test_the_committed_snapshot_is_what_the_dump_writes(self) -> None:
        # Everything, not just the catalogue: the articles and release notes
        # in this file are transcribed editorial copy, and a stale one is a
        # misquotation.
        snapshot = json.loads(
            (Path(press_catalog.__file__).with_name("_press_data.json")).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            snapshot,
            self.js,
            "server/cedar_press/_press_data.json is stale: re-run "
            "`node scripts/dump-press.mjs > server/cedar_press/_press_data.json`",
        )

    def test_the_same_collections_in_the_same_order(self) -> None:
        self.assertEqual(
            [entry["id"] for entry in press_catalog.CATALOG],
            [entry["id"] for entry in self.js["catalog"]],
        )

    def test_every_catalog_field_matches_value_for_value(self) -> None:
        for python, javascript in zip(press_catalog.CATALOG, self.js["catalog"], strict=True):
            with self.subTest(collection=javascript["id"]):
                self.assertEqual(set(python), set(javascript))
                for key in javascript:
                    with self.subTest(field=key):
                        self.assertEqual(_plain(python[key]), javascript[key])

    # -- coverage, which is a claim to a paying subscriber -----------------

    def test_every_collection_states_its_coverage_on_both_sides(self) -> None:
        # The field this class was extended for. Coverage used to be a pair,
        # `standardFrom` and `historyFrom`, and a Cedar Press reader received
        # the first while Cedar Press+ opened the second. One axis replaced
        # the two on 2026-09-02, and nothing had ever compared either number
        # across the two languages.
        for python, javascript in zip(press_catalog.CATALOG, self.js["catalog"], strict=True):
            with self.subTest(collection=javascript["id"]):
                self.assertEqual(_plain(python["coverage"]), javascript["coverage"])

    def test_coverage_is_a_series_or_a_roster_and_never_both(self) -> None:
        # The shape is the point. Two of these collections are rosters -- the
        # TERO and commerce offices behind Owned publish who is certified now
        # and archive nothing, and the IRS Business Master File behind
        # Nonprofits states the organisations that exist now -- so a field
        # that were always a year would force both to name one, and the only
        # years available are accidents: one certification that started in
        # 1992, one defunct filer whose last return was 1983. A roster
        # carrying a `from` is that defect coming back.
        for entry in press_catalog.CATALOG:
            with self.subTest(collection=entry["id"]):
                coverage = entry["coverage"]
                self.assertIn(coverage["kind"], {"series", "roster"})
                if coverage["kind"] == "series":
                    self.assertIn("from", coverage)
                    self.assertNotIn("captured", coverage)
                else:
                    self.assertIn("captured", coverage)
                    self.assertNotIn("from", coverage)

    def test_the_two_rosters_are_the_two_that_have_no_series(self) -> None:
        rosters = {
            entry["id"] for entry in press_catalog.CATALOG if entry["coverage"]["kind"] == "roster"
        }
        self.assertEqual(rosters, {"owned", "nonprofits"})

    def test_the_retired_pair_is_gone_rather_than_aliased(self) -> None:
        # A `standardFrom` set equal to the coverage year on every entry would
        # read to the next person as a live second axis, and would be one
        # edit away from being one again. It has to be absent.
        for entry in press_catalog.CATALOG:
            with self.subTest(collection=entry["id"]):
                self.assertNotIn("standardFrom", entry)
                self.assertNotIn("historyFrom", entry)
                self.assertNotIn("coverageFrom", entry)

    def test_no_coverage_value_is_a_placeholder_or_in_the_future(self) -> None:
        # Every value here was measured against the file a subscriber
        # receives, `dist/customer/<id>.csv`. That file is not in this
        # repository, so this cannot re-measure -- what it can do is refuse
        # the shapes a measurement never produces.
        this_year = datetime.datetime.now(tz=datetime.timezone.utc).year
        for entry in press_catalog.CATALOG:
            coverage = entry["coverage"]
            with self.subTest(collection=entry["id"]):
                if coverage["kind"] == "series":
                    self.assertIsInstance(coverage["from"], int)
                    self.assertGreaterEqual(coverage["from"], 1800)
                    self.assertLessEqual(coverage["from"], this_year)
                else:
                    captured = datetime.date.fromisoformat(coverage["captured"])
                    self.assertLessEqual(captured.year, this_year)

    def test_the_flag_corrected_floor_is_the_corrected_one(self) -> None:
        # min(year) is not coverage, and this is the collection where the
        # difference is a claim rather than a rounding error.
        #
        # subcontracting's unfiltered minimum is 2001, built entirely on 51
        # rows the repository itself flags `action_date_precedes_ffata_flag`
        # -- filer typos, every one filed in 2010 or later. FFATA dropped the
        # subaward reporting threshold in October 2010, so FSRS holds nothing
        # before FY2010 and 2001 would sell nine years that do not exist.
        by_id = {entry["id"]: entry for entry in press_catalog.CATALOG}
        self.assertEqual(by_id["subcontracting"]["coverage"]["from"], 2010)

    def test_a_roster_never_produces_a_coverage_from_in_a_profile(self) -> None:
        # The Python surface, not the data: `profile_for` is what Cedar
        # answers from, and a roster reaching it as a year is how a harvest
        # date becomes a coverage claim in a sentence.
        for dataset_id in ("owned", "nonprofits"):
            profile = collection_profiles.profile_for(dataset_id)
            with self.subTest(collection=dataset_id):
                self.assertEqual(profile["coverage_kind"], "roster")
                self.assertIsNone(profile["coverage_from"])
                self.assertTrue(profile["coverage_captured"])
                sentence = collection_profiles.answer_from_profile(
                    "What does this collection cover?", dataset_id
                )["answer"]
                self.assertIn("current roster rather than a series", sentence)
                self.assertNotIn("Coverage from", sentence)

    def test_the_ladder_is_six_collections_and_six_more(self) -> None:
        # The owner's ruling of 2026-09-02: Cedar Press is the standard
        # shelf at full depth, Cedar Press+ is that plus the pro shelf. The
        # counts are what the tier copy promises, so they are pinned.
        shelves: dict[str, set[str]] = {}
        for entry in press_catalog.CATALOG:
            shelves.setdefault(entry["shelf"], set()).add(entry["id"])
        self.assertEqual(len(shelves["standard"]), 6)
        self.assertEqual(
            shelves["pro"],
            {
                "contractors",
                "subcontracting",
                "owned",
                "nest",
                "natural-resources",
                "nonprofits",
            },
        )


class TestGeneratorAndManifestAgree(unittest.TestCase):
    """The importer's declarations and the manifest it writes, held equal.

    ``scripts/import_cedar_manifest.py`` declares which collections ship
    (``STOREFRONT``) and which are excluded with what reason (``EXCLUDED``),
    and copies both into ``data/cedar/collections.manifest.json``. The
    generator's other inputs -- Cedar's descriptors and review bundle -- are
    not in this tree, so the manifest cannot be regenerated here, and an edit
    to a reason in the script is an edit the manifest does not see until
    somebody with the workspace re-runs it. That is how the gaming exclusion
    read "the catalog already shows it as a Grove-exclusive preview" after
    the preview was withdrawn. These compare the two on every run.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "import_cedar_manifest", _REPO / "scripts" / "import_cedar_manifest.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        cls.script = module
        cls.manifest = json.loads(
            (_REPO / "data" / "cedar" / "collections.manifest.json").read_text(encoding="utf-8")
        )

    def test_the_storefront_order_is_the_scripts(self) -> None:
        self.assertEqual(
            [entry["id"] for entry in self.manifest["collections"]],
            list(self.script.STOREFRONT),
        )

    def test_every_exclusion_carries_the_scripts_reason(self) -> None:
        manifest = {entry["id"]: entry["reason"] for entry in self.manifest["excluded"]}
        self.assertEqual(set(manifest), set(self.script.EXCLUDED))
        for collection_id, reason in self.script.EXCLUDED.items():
            with self.subTest(excluded=collection_id):
                self.assertEqual(manifest[collection_id], reason)

    def test_the_unmeasured_fields_are_the_scripts(self) -> None:
        self.assertEqual(self.manifest["unmeasured_fields"], self.script.UNMEASURED)

    def test_nothing_is_both_shipped_and_excluded(self) -> None:
        self.assertEqual(set(self.script.STOREFRONT) & set(self.script.EXCLUDED), set())

    def test_the_unpublished_sample_record_matches_the_disk(self) -> None:
        # The record is measured, so it must agree with the checkout: a sample
        # added (or removed) without re-running the measurement fails here,
        # naming the command, on the machine where it happened.
        result = subprocess.run(  # noqa: S603
            ["node", str(_REPO / "scripts" / "measure-samples.mjs"), "--check"],
            capture_output=True, text=True, check=False, cwd=_REPO,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_the_explore_contracts_match_the_samples(self) -> None:
        # The Explore card reads each table through a contract derived from
        # its sample header (scripts/derive-explore.mjs). A sample whose
        # columns changed without the contract following fails here, naming
        # the command; so does a register export behind the spine.
        result = subprocess.run(  # noqa: S603
            ["node", str(_REPO / "scripts" / "derive-explore.mjs"), "--check"],
            capture_output=True, text=True, check=False, cwd=_REPO,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_the_release_ledger_is_tracked(self) -> None:
        # Codex, PR #52. `.gitignore` excludes `/data/*` as a directory, so a
        # file the site imports from data/cedar/ reaches the repository only
        # by `git add -f`. The first ledger was written, read by the build and
        # never committed, and `main` could not build. Every file the client
        # imports from data/cedar/ must be in the index.
        for name in ("collections.manifest.json", "releases.json",
                     "samples.published.json", "explore.json",
                     "explore.overrides.json"):
            with self.subTest(file=name):
                result = subprocess.run(  # noqa: S603
                    ["git", "-C", str(_REPO), "ls-files", "--error-unmatch",
                     f"data/cedar/{name}"],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"data/cedar/{name} is not tracked; `git add -f data/cedar/{name}`",
                )


def _plain(value: Any) -> Any:
    """A frozen snapshot value in the shape ``json`` produced it."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _listify_points(figure: dict) -> dict:
    """A dataclass holds points as a tuple; JSON has only lists."""
    return {**figure, "points": list(figure["points"])}


def _normalise_figure(figure: dict) -> dict:
    """The JS figure in the Python dataclass's shape.

    ``compare`` is absent on a single-series point in JavaScript and ``None``
    in Python; that is the two languages spelling the same absence, not a
    difference worth failing on.
    """
    return {
        **figure,
        "points": [
            {"label": p["label"], "value": p["value"], "compare": p.get("compare")}
            for p in figure["points"]
        ],
    }


def _camel(finding: dict) -> dict:
    """A supported finding in the JavaScript surface's key names."""
    finding = dict(finding)
    finding["claimClass"] = finding.pop("claim_class")
    finding["recipeId"] = finding.pop("recipe_id")
    return finding


def _listify(lead: dict) -> dict:
    """Tuples are lists once JSON has been through them."""
    return {**lead, "missing": list(lead["missing"]), "requires": list(lead["requires"])}


if __name__ == "__main__":
    unittest.main()
