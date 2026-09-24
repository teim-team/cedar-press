"""Cedar is the ONE issuer of Gaming object IDs (repository split 2026-09-24).

Lumecon-data PROPOSES bindings inside the blocks ``cedar_ids`` reserves and
never marks an ID issued; ``code/build.py gaming-issue-ids`` is the controlled
Cedar step that does, reading a PROPOSED artifact pinned by hash and writing
Cedar's live register plus a content-addressed registry snapshot for Lumecon to
pin. All fixtures are fictional; nothing here touches a real register.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import cedar_ids  # noqa: E402

SPEC = importlib.util.spec_from_file_location("gaming_issuance_build", CODE / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def binding(n, status="PROPOSED", klass="GPAY", prefix="CEDAR-EVENT"):
    key = json.dumps([klass, "fixture", str(n)])
    return {"object_prefix": prefix, "key_class": klass, "source_key": key,
            "source_key_sha256": BUILD.gaming_source_key_sha256(key),
            "issued_id": cedar_ids.format_id(prefix, cedar_ids.GAMING_BLOCKS[prefix][0] + n),
            "table": "fixture.csv", "column": "payment_event_id", "status": status,
            "first_seen_as_of": "2026-09-24"}


class GamingBlocksTest(unittest.TestCase):
    """The blocks live in cedar_ids itself, declared at import, so every
    allocate() in every process steps over them."""

    def test_allocate_steps_over_every_gaming_block(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(cedar_ids, "REGISTRY", Path(temp) / "_id_registry.json"), \
                patch.object(cedar_ids, "LOCK", Path(temp) / "_id_registry.lock"):
            for prefix, (lo, hi) in cedar_ids.GAMING_BLOCKS.items():
                (Path(temp) / "_id_registry.json").write_text(
                    json.dumps({"counters": {prefix: lo - 2}, "types": {}}), encoding="utf-8")
                got = cedar_ids.allocate(prefix, 2)
                self.assertEqual(got, [cedar_ids.format_id(prefix, lo - 1),
                                       cedar_ids.format_id(prefix, hi + 1)], prefix)
                self.assertIsNone(cedar_ids.gaming_block_ordinal(got[1]))

    def test_overlapping_declaration_by_another_owner_is_refused(self):
        lo, hi = cedar_ids.GAMING_BLOCKS["CEDAR-REL"]
        with self.assertRaises(cedar_ids.IdCollision):
            cedar_ids.declare_static_block("CEDAR-REL", hi, hi + 10, "someone else", "fixture")
        cedar_ids.declare_static_block("CEDAR-REL", lo, hi, cedar_ids.GAMING_BLOCK_OWNER,
                                       cedar_ids.GAMING_BLOCK_WHY)  # idempotent

    def test_lumecon_proposes_inside_exactly_these_blocks(self):
        """Lumecon's proposal constants must equal Cedar's reservation (never
        the other way round). Runs where the Lumecon branch is installed."""
        try:
            from lumecon_data.gaming import contract as lumecon_gaming
        except ImportError:
            self.skipTest("lumecon_data.gaming not installed (Lumecon branch claude/gaming-grove-release)")
        blocks = getattr(lumecon_gaming, "GAMING_BLOCKS", None)
        if blocks is None:
            self.skipTest("installed lumecon_data.gaming exposes no GAMING_BLOCKS")
        self.assertEqual({p: tuple(b) for p, b in blocks.items()}, cedar_ids.GAMING_BLOCKS)


class GamingIssuanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "cedar"
        self.live = self.root / BUILD.GAMING_BINDINGS

    def proposal(self, rows, name="proposed.csv"):
        path = Path(self.temp.name) / name
        path.write_bytes(BUILD._gaming_bindings_bytes(rows))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def run_issue(self, path, digest, registry, **extra):
        args = argparse.Namespace(proposed=str(path), proposed_sha256=digest, registry_sha256=registry,
                                  live_root=str(self.root), execute=False, certificate=None,
                                  decision_id=None, approved_by=None)
        for key, value in extra.items():
            setattr(args, key, value)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = BUILD.cmd_gaming_issue_ids(args)
        return code, out.getvalue()

    def execute(self, path, digest, registry):
        return self.run_issue(path, digest, registry, execute=True, certificate="CODEX-CERT-FIXTURE",
                              decision_id="DECISION-FIXTURE", approved_by="fixture")

    def test_dry_run_then_execute_then_reuse_emits_a_pinnable_snapshot(self):
        path, digest = self.proposal([binding(0), binding(1)])
        code, out = self.run_issue(path, digest, "ABSENT")
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", out)
        self.assertFalse(self.live.exists())
        with self.assertRaisesRegex(SystemExit, "needs --certificate"):
            self.run_issue(path, digest, "ABSENT", execute=True)
        self.execute(path, digest, "ABSENT")
        rows = BUILD.read_gaming_bindings(self.live)
        self.assertEqual({r["status"] for r in rows}, {"ISSUED"})
        after = hashlib.sha256(self.live.read_bytes()).hexdigest()
        snapshot = self.root / BUILD.GAMING_SNAPSHOTS / f"gaming_id_bindings.{after}.csv"
        self.assertEqual(snapshot.read_bytes(), self.live.read_bytes())
        log = [json.loads(line) for line in
               (self.live.parent / "gaming_id_issuance_log.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual((log[-1]["registry_sha256_after"], log[-1]["decision_id"]), (after, "DECISION-FIXTURE"))
        # The next Lumecon proposal, built from that snapshot, keeps the issued
        # rows byte-exact and proposes one more; stale snapshots are refused.
        path2, digest2 = self.proposal(rows + [binding(2)], "proposed2.csv")
        with self.assertRaisesRegex(SystemExit, "rebuild the proposal"):
            self.run_issue(path2, digest2, "ABSENT")
        code, out = self.run_issue(path2, digest2, after)
        self.assertEqual(json.loads(out.split("DRY RUN")[0])["issue"], {"CEDAR-EVENT": 1})

    def test_unpinned_reassigned_dropped_or_self_issued_proposals_are_refused(self):
        path, digest = self.proposal([binding(0)])
        with self.assertRaisesRegex(SystemExit, "not the one pinned"):
            self.run_issue(path, "0" * 64, "ABSENT")
        self.execute(path, digest, "ABSENT")
        live_sha = hashlib.sha256(self.live.read_bytes()).hexdigest()
        issued = BUILD.read_gaming_bindings(self.live)
        moved = dict(issued[0], issued_id=binding(5)["issued_id"])
        for rows, pattern in [
            ([], "disappeared"),
            ([moved], "disappeared|reassigned"),
            (issued + [binding(3, status="ISSUED")], "claim ISSUED without Cedar issuance"),
            (issued + [dict(binding(4), issued_id="CEDAR-EVENT-000001")], "outside the Cedar Gaming"),
        ]:
            with self.subTest(pattern=pattern):
                bad, bad_digest = self.proposal(rows, "bad.csv")
                with self.assertRaisesRegex(SystemExit, pattern):
                    self.run_issue(bad, bad_digest, live_sha)
        self.assertEqual(hashlib.sha256(self.live.read_bytes()).hexdigest(), live_sha)


if __name__ == "__main__":
    unittest.main()
