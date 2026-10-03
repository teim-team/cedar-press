"""No new tracked file names one person's machine.

A path such as ``C:\\Users\\<name>\\Desktop\\...`` works on one laptop, says
who wrote the line, and breaks when the work moves to another machine or to
CI. Living documents name places by role (``<cedar-press checkout>``,
``<checkpoint root>``) and code reads them from arguments or the environment.

The files below predate this rule: legacy ``code/`` scripts that are being
retired into Lumecon-data producers, dated build logs, and content-addressed
release artifacts whose bytes must not change. The list may only shrink. A
file that stops matching must leave it, so the baseline never hides a regression.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MACHINE_PATH = re.compile(
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'`]+"  # C:\Users\name, C:/Users/name
    r"|(?<![\w.])/Users/[A-Za-z][\w.-]*/"  # /Users/name/ (macOS)
    r"|(?<![\w.])/home/[a-z][\w.-]*/"  # /home/name/ (Linux)
)
THIS_FILE = "server/tests/test_portable_paths.py"
GRANDFATHERED = frozenset({
    "Federal Spending/code/fed_funding_do_file.do",
    "Federal Spending/code/fed_funding_do_file_corrtd.do",
    "code/01_build_entity_spine.py",
    "code/04_spiderweb_expand.py",
    "code/08_build_review_page.py",
    "code/1092_bill_titles_residue_and_scope.py",
    "code/1130_need_owner_v6_reconcile.py",
    "code/14_copy_votingpatterns_sources.py",
    "code/14_pull_cosponsors.py",
    "code/156_stage_form5500_gaming_employment.py",
    "code/16_federal_funding_recon.py",
    "code/16_profile_fedfunding_dta.do",
    "code/16c_copy_funding_inputs.py",
    "code/17_build_nonprofit_990.py",
    "code/23c_copy_directory_core_sources.py",
    "code/369_courtlistener_budget_drain.sh",
    "code/36_build_nho_intertribal.py",
    "code/434_pull_sam_entity_management.py",
    "code/516_release_manifest.py",
    "code/572_ws2_contracts.py",
    "code/67_sam_entity_harvest.py",
    "code/73_bills_votes_completion.py",
    "code/93_build_leverage_cards.py",
    "code/98_build_oira_and_hearings.py",
    "code/ancsa_v2/ocr_run.py",
    "code/ancsa_v2/ocr_run_v2.py",
    "code/cedar_keys_env.py",
    "code/collect_subawards_after_deadline.ps1",
    "code/retry_sam_downloads.ps1",
    "code/shard_g_build_crosswalk.py",
    "code/shard_g_registry_pull.py",
    "docs/ANCSA_PORTAL_V2_LOG.md",
    "docs/ANNUAL_REPORT_ORG_DISCOVERY_LOG.md",
    "docs/ARCHITECTURE_DECISIONS.md",
    "docs/BILLS_VOTES_BUILD_LOG_2026-08-05.md",
    "docs/COMPACTS_BUILD_LOG_2026-08-05.md",
    "docs/COMPETITIVE_POSITION.md",
    "docs/DEWEY_BRIEF_FOR_ANOTHER_INSTANCE.md",
    "docs/DISCOVERY_GAP.json",
    "docs/FEDERAL_FUNDING_RECONCILIATION_2026-08-05.md",
    "docs/FPDS_HIERARCHY_BUILD_LOG_2026-08-05.md",
    "docs/GAMING_SOURCE_AUDIT_2026-08-26.md",
    "docs/NEED_BUILD_LOG.md",
    "docs/PRE2007_FPDS_VS_PRIME_OVERLAP.json",
    "docs/PRE2007_IDENTIFIER_BY_AGENCY.json",
    "docs/PRE2007_IDENTIFIER_SURFACE.json",
    "docs/RELEASE_REPLAY_LOG.md",
    "docs/SHIP_GAP_REPORT.json",
    "docs/SOURCE_FRESHNESS.json",
    "docs/UNFINISHED_WORK_AUDIT.md",
    "docs/WS2_GRAIN_AND_REBUILD.md",
    "docs/lint_bug_classes.json",
    "docs/methodology/legislation.md",
    "docs/releases/nagpra-0de7096/manifest.json",
    "docs/releases/nagpra-0de7096/replay_compare.json",
    "docs/releases/nagpra-6c92a41/manifest.json",
    "docs/releases/nagpra-6c92a41/replay_compare.json",
    "docs/releases/native-owned-businesses-6c92a41/manifest.json",
    "docs/releases/native-owned-businesses-6c92a41/replay_compare.json",
    "docs/releases/natural-resources-6c92a41/manifest.json",
    "docs/releases/natural-resources-6c92a41/replay_compare.json",
    "docs/releases/subcontracting-6c92a41/manifest.json",
    "docs/releases/subcontracting-6c92a41/replay_compare.json",
    "docs/schema/c8_rebuild_proof.json",
    "docs/schema/inventory.json",
})


def _tracked() -> list[str] | None:
    git = shutil.which("git")
    if not git or not (ROOT / ".git").exists():
        return None
    listed = subprocess.run(  # noqa: S603 - fixed argument list, no outside input
        [git, "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.split(b"\0")
    return [name.decode() for name in listed if name]


def _offenders(names: list[str]) -> set[str]:
    found = set()
    for name in names:
        if name == THIS_FILE:
            continue
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        if MACHINE_PATH.search(text):
            found.add(name)
    return found


class PortablePathsTest(unittest.TestCase):
    def test_no_new_file_names_a_personal_machine_path(self):
        names = _tracked()
        if names is None:
            self.skipTest("needs a git checkout to list tracked files")
        offenders = _offenders(names)
        self.assertEqual(sorted(offenders - GRANDFATHERED), [])
        self.assertEqual(
            sorted(GRANDFATHERED - offenders),
            [],
            "these files no longer carry a machine path; remove them from GRANDFATHERED",
        )

    def test_the_pattern_catches_each_platform_and_spares_placeholders(self):
        for machine in (
            r"C:\Users\someone\Desktop\Cedar Press",
            "C:/Users/someone/work",
            "/Users/someone/code",
            "/home/someone/data",
        ):
            self.assertRegex(machine, MACHINE_PATH)
        for portable in ("<cedar-press checkout>/server", "~/Downloads", "src/users.py"):
            self.assertNotRegex(portable, MACHINE_PATH)


if __name__ == "__main__":
    unittest.main()
