"""The cross-language contract: Python and JavaScript hold one access rule.

``src/features/grove/pressAccess.js`` decides what the browser renders and
``server/cedar_press/repository.py`` decides what the API serves. Both said so
in their own comments, and both said the two must answer identically::

    #: Which shelf each plan reaches. Mirrors ``features/grove/pressAccess.js``;
    #: the client decides what renders and this decides what is served, and the
    #: two are written to answer identically.

Nothing compared them. They had drifted by exactly one tier: ``tree`` was in
the server's ``SHELF_BY_TIER`` and missing from the client's ``PLAN_REACH``, so
a Tree subscriber was served twelve collections by ``GET /press/collections``
and shown none of them on the shelf. ``press_catalog.py`` separately claimed
that ``PRESS_TIERS`` and the JavaScript "can be compared as sets by the parity
test", and there was no parity test either.

This is the check, in the same shape as ``test_collection.py``: it executes
BOTH implementations -- Python in-process, JavaScript through
``scripts/dump-access.mjs`` -- and compares what they answer.

TWO QUESTIONS, COMPARED SEPARATELY
    "Is this plan sold the Cedar Press page?" and "which collections does this
    plan open?" have different answers for ``grove`` and for ``tree``: both
    reach every shelf, because Cedar Grove carries every dataset and Tree
    includes Grove, and neither is sold the storefront. Running the two
    together is what produced the drift, so they are compared as two maps
    rather than reconciled into one.

If ``node`` is unavailable the test FAILS rather than skipping, for the reason
``test_collection.py`` gives: an unrun parity check is how the two drifted the
first time.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from cedar_press import collections as launch
from cedar_press import press_catalog, repository

_REPO = Path(__file__).resolve().parents[2]
_DUMP = _REPO / "scripts" / "dump-access.mjs"


def _javascript() -> dict:
    """Run the JavaScript access rules and read back what they answer."""
    node = shutil.which("node")
    if node is None:
        raise AssertionError("node is not on PATH")
    result = subprocess.run(  # noqa: S603
        [node, str(_DUMP)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=_REPO,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"scripts/dump-access.mjs exited {result.returncode}:\n{result.stderr}"
        )
    return json.loads(result.stdout)


class TestAccessParity(unittest.TestCase):
    """The client's access map and the server's, compared key for key."""

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise AssertionError(
                "node is not on PATH, so the two access maps cannot be compared. "
                "This fails rather than skips: an unrun parity check is how the "
                "two drifted the first time."
            )
        cls.js = _javascript()

    # -- which shelves a plan reaches --------------------------------------

    def test_the_two_maps_carry_the_same_keys(self) -> None:
        # The failure this test exists for. A tier present in one map and
        # absent from the other is served data the page will not show, or
        # shown a card the API will refuse, and neither side can detect it
        # alone. Compared as key sets first so the report names the missing
        # tier rather than one wrong answer.
        self.assertEqual(
            set(repository.SHELF_BY_TIER),
            set(self.js["planReach"]),
        )

    def test_the_two_maps_agree_on_every_shelf(self) -> None:
        self.assertEqual(repository.SHELF_BY_TIER, self.js["planReach"])

    def test_tree_reaches_the_grove_shelf_on_both_sides(self) -> None:
        # Pinned by name because this is the tier that drifted, and because
        # the reason is a product fact rather than a symmetry: Tree includes
        # Cedar Grove and Cedar Grove carries every dataset.
        self.assertEqual(repository.SHELF_BY_TIER["tree"], "grove")
        self.assertEqual(self.js["planReach"]["tree"], "grove")

    def test_every_tier_resolves_to_the_same_reach(self) -> None:
        # PLAN_REACH is the declaration; shelfReach is the answer, and it
        # folds in the unknown-tier fallback. Both sides must fall back to
        # "nothing", not to the cheapest shelf.
        for tier, reach in self.js["shelfReach"].items():
            with self.subTest(tier=tier):
                self.assertEqual(repository.SHELF_BY_TIER.get(tier), reach)

    def test_the_shelves_and_their_order_agree(self) -> None:
        self.assertEqual(
            set(repository.SHELF_ORDER),
            set(self.js["shelves"].values()),
        )
        # Nesting is what makes "reaches" a comparison rather than a lookup,
        # so the order has to be the same order and not merely the same set.
        self.assertEqual(
            list(repository.SHELF_ORDER),
            list(self.js["shelves"].values()),
        )

    def test_the_same_collections_open_for_every_tier(self) -> None:
        # The end-to-end form of the drift, stated in collections rather than
        # in shelf names: this is the count a subscriber actually sees.
        for tier, reach in self.js["shelfReach"].items():
            with self.subTest(tier=tier):
                order = list(repository.SHELF_ORDER)
                expected = [
                    d.id
                    for d in launch.LAUNCH_COLLECTION
                    if reach is not None and order.index(d.shelf) <= order.index(reach)
                ]
                served = [d["id"] for d in repository.collections_for(tier)]
                self.assertEqual(served, expected)

    # -- who is sold the page ----------------------------------------------

    def test_the_page_opens_for_the_same_tiers_on_both_sides(self) -> None:
        for tier, can_read in self.js["canReadCedarPress"].items():
            with self.subTest(tier=tier):
                self.assertEqual(press_catalog.can_read_cedar_press(tier), can_read)

    def test_press_tiers_is_exactly_the_set_that_reads_the_page(self) -> None:
        # The set the docstring of ``PRESS_TIERS`` promised was compared.
        self.assertEqual(
            press_catalog.PRESS_TIERS,
            frozenset(t for t, ok in self.js["canReadCedarPress"].items() if ok),
        )

    def test_reaching_a_shelf_is_not_being_sold_the_page(self) -> None:
        # The distinction the two maps exist to keep apart. Grove and Tree
        # reach every shelf and are sold neither the storefront nor a Cedar
        # Press subscription; if this ever becomes symmetric it should be
        # because the commercial arrangement changed, not because someone
        # simplified two maps into one.
        for tier in ("grove", "tree"):
            with self.subTest(tier=tier):
                self.assertEqual(repository.SHELF_BY_TIER[tier], "grove")
                self.assertFalse(press_catalog.can_read_cedar_press(tier))

    def test_an_unknown_tier_is_refused_by_both(self) -> None:
        for tier in ("", "bogus", "penthouse"):
            with self.subTest(tier=tier):
                self.assertIsNone(repository.SHELF_BY_TIER.get(tier))
                self.assertEqual(repository.collections_for(tier), [])
                self.assertFalse(press_catalog.can_read_cedar_press(tier))


class TestGroveDivergence(unittest.TestCase):
    """Where Cedar Grove carries a dataset Cedar Press does not.

    Cedar Grove is a superset of Cedar Press by content. The site has to be
    able to say that without implying a Press reader is missing something they
    were sold, and it has to say it in the vocabulary the Cedar data workspace
    already uses rather than a second one invented here.

    That vocabulary is ``code/cedar_publication.py``: ``CUSTOMER_SHELVES =
    ("standard", "pro")`` are the shelves a paying Cedar Press customer sees,
    and the other shelf values -- ``grove``, ``withdrawn``, ``infrastructure``
    -- are each a different reason a measured collection is not on the
    storefront. ``scripts/import_cedar_manifest.py`` carries that split into
    ``data/cedar/collections.manifest.json`` as ``collections`` and
    ``excluded``, and both language implementations read that file.

    These tests pin the site to it. Nothing here compared the catalog's
    ``grove`` shelf against the workspace's, so the two could have disagreed
    about which collection is Grove-exclusive with nothing to notice.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise AssertionError("node is not on PATH")
        cls.js = _javascript()

    def test_the_customer_shelves_are_the_launch_collection(self) -> None:
        # Six and six, the twelve the owner ruled on 2026-09-02. Stated as the
        # two shelves rather than as a total, because the total is what a
        # Grove-shelf collection would silently join.
        by_shelf: dict[str, list[str]] = {}
        for dataset in launch.LAUNCH_COLLECTION:
            by_shelf.setdefault(dataset.shelf, []).append(dataset.id)
        self.assertEqual(set(by_shelf), {"standard", "pro"})
        self.assertEqual(len(by_shelf["standard"]), 6)
        self.assertEqual(len(by_shelf["pro"]), 6)

    def test_the_catalog_is_the_storefront_plus_the_grove_shelf(self) -> None:
        # Thirteen in the catalog, twelve on the storefront. The difference is
        # the Grove shelf, and it is exactly one collection today.
        catalog = self.js["catalogByShelf"]
        self.assertEqual(set(catalog), {"standard", "pro", "grove"})
        storefront = sorted(catalog["standard"] + catalog["pro"])
        self.assertEqual(storefront, sorted(d.id for d in launch.LAUNCH_COLLECTION))
        self.assertEqual(len(storefront), 12)
        self.assertEqual(sum(len(v) for v in catalog.values()), 13)

    def test_the_grove_shelf_matches_the_workspace_assignment(self) -> None:
        # The catalog says which collections are Grove-exclusive; the manifest
        # says which the Cedar data workspace put on shelf "grove". A
        # disagreement here is the site selling, or withholding, a collection
        # on its own authority.
        catalog_grove = set(self.js["catalogByShelf"].get("grove", []))
        workspace_grove = {
            entry["id"]
            for entry in launch.EXCLUDED_COLLECTIONS
            if entry["shelf"] == "grove"
        }
        self.assertEqual(catalog_grove, workspace_grove)
        self.assertEqual(catalog_grove, {"gaming"})

    def test_a_grove_shelf_collection_is_never_on_the_storefront(self) -> None:
        # The one direction that must never happen: a Grove-exclusive
        # collection appearing in what a Press subscription serves.
        for tier in ("press", "press_pro"):
            with self.subTest(tier=tier):
                shelves = {d["shelf"] for d in repository.collections_for(tier)}
                self.assertNotIn("grove", shelves)

    def test_every_excluded_collection_says_why_in_its_own_words(self) -> None:
        # Flag, never delete, and never with a shared reason: "grove",
        # "withdrawn" and "infrastructure" are three different facts about a
        # collection and collapsing them would make the Press/Grove boundary
        # unreadable.
        excluded = {entry["id"]: entry for entry in launch.EXCLUDED_COLLECTIONS}
        self.assertEqual(set(excluded), {"newsletters", "gaming", "_entity_layer"})
        self.assertEqual(
            {entry["shelf"] for entry in excluded.values()},
            {"standard", "grove", "infrastructure"},
        )
        for entry in excluded.values():
            with self.subTest(collection=entry["id"]):
                self.assertTrue(entry["reason"].strip())
        # Only one of the three is a Grove divergence. The other two are not
        # in Cedar Grove's favour and must not be counted as though they were.
        self.assertEqual(
            [e["id"] for e in excluded.values() if e["shelf"] == "grove"],
            ["gaming"],
        )

    def test_the_two_implementations_agree_on_what_is_excluded(self) -> None:
        self.assertEqual(
            [{"id": e["id"], "shelf": e["shelf"]} for e in launch.EXCLUDED_COLLECTIONS],
            self.js["excluded"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
