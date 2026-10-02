"""Maintained definition overrides require exact evidence and a current header."""

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_PATH = Path(__file__).resolve().parents[2] / "scripts/preview_definitions.py"
_SPEC = importlib.util.spec_from_file_location("preview_definition_override_test_subject", _PATH)
assert _SPEC and _SPEC.loader
defs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(defs)
_OVERRIDE_SPEC = importlib.util.spec_from_file_location(
    "preview_definition_override_git_test_subject",
    _PATH.with_name("preview_definition_overrides.py"),
)
assert _OVERRIDE_SPEC and _OVERRIDE_SPEC.loader
override_loader = importlib.util.module_from_spec(_OVERRIDE_SPEC)
_OVERRIDE_SPEC.loader.exec_module(override_loader)


class PreviewDefinitionOverridesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "press"
        self.producer = Path(self.temp.name) / "producer"
        self.root.mkdir()
        self.producer.mkdir()
        self.source = self.producer / "src" / "source.py"
        self.source.parent.mkdir()
        self.source.write_bytes(b"Source action date contract.\n")
        self.path = self.root / "data/cedar/preview_definition_overrides.json"
        self.path.parent.mkdir(parents=True)
        self.document = {
            "schema_version": 1,
            "evidence": {
                "source": {
                    "repository": "producer",
                    "path": "src/source.py",
                    "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                    "revision": "working-tree",
                }
            },
            "collections": {
                "funding": {
                    "action_date": {
                        "label": "Action date",
                        "meaning": "Source agency action date, distinct from the publication date.",
                        "evidence": ["source"],
                        "definition_source": {
                            "kind": "reviewed_transform_contract",
                            "path": "src/source.py",
                            "revision": "working-tree",
                        },
                    }
                }
            },
        }

    def write(self):
        self.path.write_text(json.dumps(self.document), encoding="utf-8")

    def test_verified_override_fills_placeholder_and_carries_hashes(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {"action_date": {"description": "Reviewed Cedar field contract: action_date"}},
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(
            fields[0]["meaning"], self.document["collections"]["funding"]["action_date"]["meaning"]
        )
        provenance = fields[0]["definition_source"]
        self.assertEqual(
            provenance["evidence"][0]["sha256"], self.document["evidence"]["source"]["sha256"]
        )
        self.assertEqual(
            provenance["override_file_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest()
        )
        again = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": fields[0]["meaning"],
                    "label": fields[0]["label"],
                    "definition_source": fields[0]["definition_source"],
                }
            },
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(again, fields)
        self.assertEqual(again[0]["definition_source"]["kind"], "reviewed_transform_contract")

    def test_changed_maintained_override_refreshes_its_own_previous_definition(self):
        self.write()
        first = defs.require_fields(
            "funding",
            ["action_date"],
            {},
            {},
            {},
            overrides=defs.load_overrides(self.root, self.producer),
        )
        self.document["collections"]["funding"]["action_date"]["meaning"] = (
            "The clarified source agency action date; publication is separate."
        )
        self.write()
        refreshed = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": first[0]["meaning"],
                    "definition_source": first[0]["definition_source"],
                }
            },
            {},
            {},
            overrides=defs.load_overrides(self.root, self.producer),
        )
        self.assertEqual(
            refreshed[0]["meaning"],
            self.document["collections"]["funding"]["action_date"]["meaning"],
        )
        self.assertNotEqual(
            refreshed[0]["definition_source"]["override_file_sha256"],
            first[0]["definition_source"]["override_file_sha256"],
        )

    def test_changed_evidence_and_missing_producer_are_refused(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "requires --producer"):
            defs.load_overrides(self.root)
        self.source.write_bytes(b"Changed contract.\n")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            defs.load_overrides(self.root, self.producer)

    def test_override_does_not_replace_substantive_current_definition(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        evidence = {"kind": "pinned_current_contract", "sha256": "b" * 64}
        fields = defs.require_fields(
            "funding",
            ["action_date"],
            {
                "action_date": {
                    "description": "The exact existing agency action date.",
                    "definition_source": evidence,
                }
            },
            {},
            {},
            overrides=overrides,
        )
        self.assertEqual(fields[0]["meaning"], "The exact existing agency action date.")
        self.assertEqual(fields[0]["definition_source"], evidence)

    def test_unknown_current_column_does_not_silently_use_old_override(self):
        self.write()
        overrides = defs.load_overrides(self.root, self.producer)
        with self.assertRaisesRegex(ValueError, "absent from current"):
            defs.require_fields("funding", ["new_date"], {}, {}, {}, overrides=overrides)

    def test_definition_provenance_must_match_referenced_path_and_revision(self):
        for key, value in [("path", "src/other.py"), ("revision", "b" * 40)]:
            with self.subTest(key=key):
                source = self.document["collections"]["funding"]["action_date"]["definition_source"]
                previous = source[key]
                source[key] = value
                self.write()
                with self.assertRaisesRegex(ValueError, "not covered"):
                    defs.load_overrides(self.root, self.producer)
                source[key] = previous

    def test_placeholder_override_and_duplicate_json_keys_are_refused(self):
        self.document["collections"]["funding"]["action_date"]["meaning"] = "action date"
        self.write()
        with self.assertRaisesRegex(ValueError, "Substantive override"):
            defs.load_overrides(self.root, self.producer)
        self.path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate override"):
            defs.load_overrides(self.root, self.producer)

    def test_evidence_path_escape_and_silent_line_end_normalization_are_refused(self):
        self.document["evidence"]["source"]["path"] = "../outside.py"
        self.write()
        with self.assertRaisesRegex(ValueError, "escapes"):
            defs.load_overrides(self.root, self.producer)
        self.document["evidence"]["source"]["path"] = "src/source.py"
        self.write()
        self.source.write_bytes(b"Source action date contract.\r\n")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            defs.load_overrides(self.root, self.producer)

    def test_namespaced_source_field_labels_are_not_substantive_definitions(self):
        for value in ["source_system", "source system"]:
            self.assertFalse(defs.is_substantive(value, "documents__source_system"))
        self.assertTrue(
            defs.is_substantive(
                "Original Federal Register source-system label.", "documents__source_system"
            )
        )

    def git(self, *args):
        hooks = Path(self.temp.name) / "empty-hooks"
        hooks.mkdir(exist_ok=True)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.producer),
                "-c",
                "core.autocrlf=false",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "core.hooksPath=" + str(hooks),
                "-c",
                "user.name=Evidence Test",
                "-c",
                "user.email=evidence-test@example.invalid",
                *args,
            ],
            capture_output=True,
            env=override_loader._git_environment(),
            timeout=15,
            check=True,
        )
        return result.stdout.decode("utf-8").strip()

    def pin_commit(self):
        self.git("init", "--quiet", "--object-format=sha1")
        self.git("add", "--force", "--", "src/source.py")
        self.git("commit", "--quiet", "-m", "Pinned evidence fixture")
        revision = self.git("rev-parse", "HEAD")
        self.set_revision(revision)
        self.document["evidence"]["source"]["sha256"] = hashlib.sha256(
            self.source.read_bytes()
        ).hexdigest()
        self.write()
        return revision

    def set_revision(self, revision):
        self.document["evidence"]["source"]["revision"] = revision
        self.document["collections"]["funding"]["action_date"]["definition_source"]["revision"] = (
            revision
        )

    def test_commit_pin_survives_working_file_edits_and_deletion(self):
        revision = self.pin_commit()
        expected = self.document["evidence"]["source"]["sha256"]
        self.source.write_bytes(b"New, uncommitted field contract.\n")
        for state in ("modified", "deleted"):
            with self.subTest(state=state):
                if state == "deleted":
                    self.source.unlink()
                result = defs.load_overrides(self.root, self.producer)
                source = result["funding"]["action_date"]["definition_source"]
                self.assertEqual(source["revision"], revision)
                self.assertEqual(source["evidence"][0]["sha256"], expected)

    def test_commit_pin_does_not_follow_new_head(self):
        revision = self.pin_commit()
        self.source.write_bytes(b"A later committed contract.\n")
        self.git("add", "--", "src/source.py")
        self.git("commit", "--quiet", "-m", "Later evidence")
        self.assertNotEqual(self.git("rev-parse", "HEAD"), revision)
        result = defs.load_overrides(self.root, self.producer)
        self.assertEqual(
            result["funding"]["action_date"]["definition_source"]["revision"], revision
        )

    def test_missing_commit_refuses_working_tree_fallback(self):
        self.pin_commit()
        self.set_revision("0" * 40)
        self.write()
        with self.assertRaisesRegex(ValueError, "unavailable locally.*no network fetch"):
            defs.load_overrides(self.root, self.producer)

    def test_commit_pin_requires_git_checkout(self):
        self.set_revision("a" * 40)
        self.write()
        with self.assertRaisesRegex(ValueError, "unavailable locally"):
            defs.load_overrides(self.root, self.producer)

    def test_commit_pin_checks_raw_hash_and_never_normalizes_line_endings(self):
        self.source.write_bytes(b"Source action date contract.\r\n")
        self.pin_commit()
        raw_digest = self.document["evidence"]["source"]["sha256"]
        self.document["evidence"]["source"]["sha256"] = hashlib.sha256(
            b"Source action date contract.\n"
        ).hexdigest()
        self.write()
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            defs.load_overrides(self.root, self.producer)
        self.document["evidence"]["source"]["sha256"] = raw_digest
        self.write()
        self.assertIn("funding", defs.load_overrides(self.root, self.producer))

    def test_commit_pin_refuses_missing_path_and_non_blob(self):
        self.pin_commit()
        for path, message in [
            ("src/missing.py", "unavailable locally"),
            ("src", "not a blob"),
        ]:
            with self.subTest(path=path):
                self.document["evidence"]["source"]["path"] = path
                self.document["collections"]["funding"]["action_date"]["definition_source"][
                    "path"
                ] = path
                self.write()
                with self.assertRaisesRegex(ValueError, message):
                    defs.load_overrides(self.root, self.producer)

    def test_tree_object_is_not_accepted_as_a_commit(self):
        self.pin_commit()
        self.set_revision(self.git("rev-parse", "HEAD^{tree}"))
        self.write()
        with self.assertRaisesRegex(ValueError, "not a full local commit"):
            defs.load_overrides(self.root, self.producer)

    def test_oversized_blob_is_refused_before_content_read(self):
        self.pin_commit()
        with (
            mock.patch.object(override_loader, "_EVIDENCE_LIMIT", 8),
            mock.patch.object(
                override_loader, "_git_command", wraps=override_loader._git_command
            ) as commands,
            self.assertRaisesRegex(ValueError, "blob exceeds bound"),
        ):
            override_loader.load(self.root, self.producer, is_substantive=defs.is_substantive)
        self.assertEqual(len(commands.call_args_list), 2)
        self.assertTrue(
            all(call.args[1].startswith("--batch-check=") for call in commands.call_args_list)
        )

    def test_commit_mode_rejects_unsafe_or_unbounded_paths(self):
        self.pin_commit()
        for path in (
            "../outside.py",
            "/absolute.py",
            "C:/outside.py",
            "src\\source.py",
            "src/source.py\nHEAD",
            "src/source.py\x00",
            "x" * 4097,
        ):
            with self.subTest(path=path):
                self.document["evidence"]["source"]["path"] = path
                self.write()
                with self.assertRaisesRegex(ValueError, "Evidence path"):
                    defs.load_overrides(self.root, self.producer)

    def test_commit_mode_rejects_unsupported_hash_mode(self):
        self.pin_commit()
        self.document["evidence"]["source"]["hash_mode"] = "normalize-newlines"
        self.write()
        with self.assertRaisesRegex(ValueError, "Unsupported evidence hash mode"):
            defs.load_overrides(self.root, self.producer)

    def test_local_object_environment_disables_fetch_and_inherited_repository(self):
        with mock.patch.dict(
            override_loader.os.environ,
            {"GIT_DIR": "elsewhere", "GIT_WORK_TREE": "elsewhere", "GIT_ALLOW_PROTOCOL": "https"},
        ):
            env = override_loader._git_environment()
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_WORK_TREE", env)
        self.assertEqual(env["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "")


if __name__ == "__main__":
    unittest.main()
