"""Fixture-only tests of the existing runner's fail-closed execution boundary."""
import argparse
import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build

class PlanSafetyTests(unittest.TestCase):
    def plan(self, **updates):
        result = dict(id="fixture", tables=["one.csv"], phase1=["build.py"],
                      phase2=[], ambiguous=[], blocked=[], rb={"build.py": ["one.csv"]}, en={})
        result.update(updates)
        return result

    def test_valid_plan(self):
        with patch.object(build.CP, "registration_problems", return_value=[]) as registration:
            self.assertEqual(build.plan_problems(self.plan()), [])
            registration.assert_called_once()

    def test_unregistered_plan_is_refused(self):
        self.assertIn("UNREGISTERED_COLLECTION", " ".join(build.plan_problems(self.plan())))

    def test_incomplete_plans_never_dispatch(self):
        cases = [
            (self.plan(tables=[]), "NO_TABLES"),
            (self.plan(phase1=[]), "NO_STAGES"),
            (self.plan(ambiguous=["other.py"]), "AMBIGUOUS_STAGES"),
            (self.plan(blocked=["other.py"]), "BLOCKED_STAGES"),
            (self.plan(rb={}), "NO_PRODUCER"),
            (self.plan(phase1=["nonexistent-fixture.py"]), "MISSING_STAGE"),
        ]
        for plan, invariant in cases:
            with self.subTest(invariant=invariant), patch.object(build, "plan_for", return_value=plan), patch.object(build.subprocess, "run") as run:
                stream = io.StringIO()
                with contextlib.redirect_stderr(stream):
                    self.assertEqual(build.cmd_run(argparse.Namespace(execute=True, collection="fixture")), 1)
                self.assertIn(invariant, stream.getvalue())
                run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
