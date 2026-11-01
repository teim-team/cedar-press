"""A finished spreadsheet is served only while it still matches the pinned release."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cedar_press import finished_sheets, governed_collections, repository, spreadsheet
from tests import test_shared_release_collections as shared_fixture

TRACT_COLUMNS = tuple(
    field["column"]
    for field in governed_collections.component_declarations("plot")["tract_observations"]["fields"]
)
ROUTE = "/press/collections/plot/spreadsheet-download"


class FinishedSheets(unittest.TestCase):
    setUp_shared = shared_fixture.SharedCollectionReleaseTest.setUp
    fixture = shared_fixture.SharedCollectionReleaseTest.fixture
    session = shared_fixture.SharedCollectionReleaseTest.session

    def setUp(self):
        self.setUp_shared()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        env = patch.dict(os.environ, {finished_sheets.FOLDER_ENV: folder.name})
        env.start()
        self.addCleanup(env.stop)
        self.manifest, self.pin, _ = self.fixture(
            component="tract_observations", columns=TRACT_COLUMNS
        )
        self.session("grove")

    def get(self, release_id=None):
        return self.client.get(ROUTE, params={"release_id": release_id or self.pin["release_id"]})

    def csv_file(self):
        return next(self.folder.glob("*.csv"))

    def no_component_bytes(self):
        return patch.object(
            repository, "_release_response", side_effect=AssertionError("Read component bytes")
        )

    def test_a_finished_file_is_served_without_rebuilding_and_equals_the_built_one(self):
        built = self.get()
        self.assertEqual(built.status_code, 200, built.text)
        finished_sheets.build("plot")
        self.assertEqual(len(list(self.folder.iterdir())), 2)
        with self.no_component_bytes():
            served = self.get()
        self.assertEqual(served.status_code, 200, served.text)
        self.assertEqual(served.content, built.content)
        for header in ("x-cedar-sha256", "x-cedar-rows", "x-cedar-citation", "content-disposition"):
            self.assertEqual(served.headers[header], built.headers[header])
        self.assertEqual(
            served.headers["x-cedar-sha256"], hashlib.sha256(served.content).hexdigest()
        )

    def test_building_twice_keeps_the_first_file(self):
        finished_sheets.build("plot")
        with self.no_component_bytes():
            _paths, built = finished_sheets.build("plot")
        self.assertFalse(built)

    def test_changed_bytes_are_never_served_and_the_request_builds_instead(self):
        finished_sheets.build("plot")
        good = self.get().content
        self.csv_file().write_bytes(b"cedar_uid\nCE-TAMPERED-00\n")
        with self.assertLogs("cedar_press.download", level="WARNING"):
            response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, good)

    def test_a_file_without_its_record_is_not_served(self):
        finished_sheets.build("plot")
        next(self.folder.glob("*.json")).unlink()
        with self.no_component_bytes(), self.assertRaises(AssertionError):
            self.get()

    def test_a_rule_change_retires_the_file(self):
        finished_sheets.build("plot")
        with (
            patch.object(finished_sheets, "_rules", return_value=b"new rules"),
            self.no_component_bytes(),
            self.assertRaises(AssertionError),
        ):
            self.get()

    def test_another_release_and_a_changed_manifest_refuse_despite_a_finished_file(self):
        finished_sheets.build("plot")
        with self.no_component_bytes():
            self.assertEqual(self.get("d" * 64).status_code, 503)
        self.manifest["components"]["tract_observations"]["record_count"] += 1
        with self.no_component_bytes():
            self.assertEqual(self.get().status_code, 503)

    def test_an_account_is_still_checked_before_a_finished_file(self):
        finished_sheets.build("plot")
        from cedar_press.accounts.services import subscribers

        with patch.object(subscribers, "find", return_value=None):
            self.assertEqual(self.get().status_code, 401)

    def test_a_failed_copy_leaves_nothing_behind(self):
        with (
            patch.object(finished_sheets.shutil, "copyfileobj", side_effect=OSError),
            self.assertRaises(OSError),
        ):
            finished_sheets.build("plot")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_main_builds_every_collection_and_removes_only_what_is_stale(self):
        finished_sheets.build("plot")
        stale = sorted(self.folder.iterdir())
        kept = {}

        def build(collection):
            paths = self.folder / f"{collection}.csv", self.folder / f"{collection}.json"
            for path in paths:
                path.write_text("{}", encoding="utf-8")
            kept[collection] = paths
            return paths, True

        with patch.object(finished_sheets, "build", side_effect=build):
            self.assertEqual(finished_sheets.main(), 0)
        self.assertEqual(
            sorted(kept), sorted(item.id for item in repository.launch.LAUNCH_COLLECTION)
        )
        self.assertFalse(any(path.exists() for path in stale))
        self.assertEqual(len(list(self.folder.iterdir())), 2 * len(kept))

    def test_main_keeps_older_files_when_a_collection_fails(self):
        finished_sheets.build("plot")
        before = sorted(self.folder.iterdir())
        with patch.object(
            finished_sheets, "build", side_effect=repository.FullReleaseUnavailable("no pin")
        ):
            self.assertEqual(finished_sheets.main(), 1)
        self.assertEqual(sorted(self.folder.iterdir()), before)

    def test_unset_folder_builds_in_the_request(self):
        with patch.dict(os.environ, {finished_sheets.FOLDER_ENV: ""}):
            self.assertIsNone(finished_sheets.open_verified("plot", {"release_id": "c" * 64}))
            self.assertEqual(self.get().status_code, 200)
            self.assertEqual(finished_sheets.main(), 1)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_the_record_is_plain_json_beside_the_file(self):
        finished_sheets.build("plot")
        record = json.loads(next(self.folder.glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(record["sha256"], hashlib.sha256(self.csv_file().read_bytes()).hexdigest())
        self.assertEqual(record["record_count"], spreadsheet.metadata("plot")["record_count"])
