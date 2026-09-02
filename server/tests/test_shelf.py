"""The server-rendered shelf: does Python actually render the site?

``docs/PYTHON_FIRST_SITE.md`` claims the collection data, the access rule and
the catalog copy are already in Python and that a page can be built from them
without reading a JavaScript module. This is the check on that claim, and it
checks the parts that would make the claim hollow if they were faked:

* the page carries the REAL collection names, versions and coverage years,
  compared against ``collections.py`` and the manifest rather than against a
  string typed into this file;
* it links the client's real stylesheets, and they are actually served;
* the tier decides only what is DESCRIBED -- the download route it points at
  still refuses a reader who is not signed in;
* it reproduces the disagreement it was built to expose, so that the day
  somebody settles the ``tree`` tier, a test fails and says so.

It also pins the two live cross-language divergences the slice found. Those
assertions are written to FAIL when the drift is fixed. That is deliberate: a
drift nobody is told about is how the collection modules got out of step twice
before ``test_collection.py`` existed, and a failing test that says "this was
fixed, delete me" is the cheapest possible notification.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("CEDAR_PRESS_SECRET", "test-secret")
os.environ.setdefault("CEDAR_PRESS_INSECURE_COOKIE", "1")
os.environ.setdefault(
    "CEDAR_PRESS_ACCOUNTS",
    json.dumps({"reader@example.org": {"password": "correct-horse", "tier": "press"}}),
)

from fastapi.testclient import TestClient  # noqa: E402
from markupsafe import escape  # noqa: E402

from cedar_press import collections as launch  # noqa: E402
from cedar_press import press_catalog, repository, shelf  # noqa: E402
from cedar_press.app import app  # noqa: E402

client = TestClient(app)

_REPO = Path(__file__).resolve().parents[2]


def _page(tier: str | None = None) -> str:
    response = client.get("/press/shelf", params={} if tier is None else {"tier": tier})
    if response.status_code != 200:
        raise AssertionError(f"/press/shelf returned {response.status_code}")
    return response.text


def _as_rendered(text: str) -> str:
    """A data string the way Jinja will have written it into the page.

    Cedar's copy is full of apostrophes and ampersands, and asserting on the
    raw value would fail on the escaping rather than on the content — which is
    a test that punishes the template for being correct.
    """
    return str(escape(text))


class TestItIsHtmlAndItIsThisService(unittest.TestCase):
    """The page exists, is HTML, and comes out of the app the API already runs."""

    def test_the_route_serves_html(self) -> None:
        response = client.get("/press/shelf")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/html"))
        self.assertTrue(response.text.lstrip().startswith("<!doctype html>"))

    def test_it_is_not_indexed_and_not_shared_cached(self) -> None:
        # The React client serves the same shelf at its own URL. Two indexed
        # URLs for one page sends a search result to the wrong one, and the
        # body differs per plan, so no shared cache may keep it.
        response = client.get("/press/shelf")
        self.assertEqual(response.headers["x-robots-tag"], "noindex")
        self.assertIn("no-store", response.headers["cache-control"])

    def test_no_route_the_client_already_uses_changed_shape(self) -> None:
        # The slice adds a surface; it must not have altered one. /health is
        # the cheapest proof the app still boots the way it did.
        self.assertEqual(client.get("/health").json(), {"status": "ok"})


class TestItRendersTheRealCollectionData(unittest.TestCase):
    """Every figure on the page traced back to the module that owns it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.body = _page("grove")

    def test_every_collection_the_manifest_declares_is_on_the_page(self) -> None:
        for dataset in launch.LAUNCH_COLLECTION:
            with self.subTest(dataset=dataset.id):
                self.assertIn(dataset.id, self.body)

    def test_each_badge_carries_the_name_the_data_gives_it(self) -> None:
        # The short name comes from the catalog where the catalog knows the
        # collection and from the descriptor where it does not. Either way it
        # is read, never typed.
        for dataset in launch.LAUNCH_COLLECTION:
            catalog = next(
                (e for e in press_catalog.CATALOG if e["id"] == dataset.id), None
            )
            expected = catalog["short"] if catalog else dataset.short_name
            with self.subTest(dataset=dataset.id):
                self.assertIn(_as_rendered(expected), self.body)

    def test_the_context_line_is_the_one_collections_py_computes(self) -> None:
        # Versions and the latest refresh date. Rendered rather than restated:
        # if this page ever disagrees with collection_context_line() it is
        # because somebody wrote a second one.
        self.assertIn(_as_rendered(launch.collection_context_line()), self.body)

    def test_no_figure_on_the_page_was_invented(self) -> None:
        # Every four-digit year the page prints must be a year the catalog or
        # a release actually states. This is the guard against a template
        # picking up a plausible-looking number from nowhere.
        stated = {str(dataset.updated)[:4] for dataset in launch.LAUNCH_COLLECTION}
        for entry in press_catalog.CATALOG:
            for field in ("standardFrom", "historyFrom"):
                if entry.get(field) is not None:
                    stated.add(str(entry[field]))
        for release in press_catalog.RELEASES.values():
            if release.get("updated"):
                stated.add(str(release["updated"])[:4])
        # Only years inside the page's own body copy, not in URLs or classes.
        printed = set(re.findall(r"\b(1[89]\d{2}|20\d{2})\b", self.body))
        self.assertTrue(
            printed <= stated,
            f"the page prints years nothing states: {sorted(printed - stated)}",
        )

    def test_the_collection_with_no_sample_says_cedars_reason_for_it(self) -> None:
        reason = launch.sample_unavailable_reason("owned")
        self.assertTrue(reason, "the fixture for this test has gone away")
        self.assertIn(_as_rendered(reason), _page("press_pro"))

    def test_excluded_collections_are_named_rather_than_absent(self) -> None:
        for entry in launch.EXCLUDED_COLLECTIONS:
            with self.subTest(excluded=entry["id"]):
                self.assertIn(_as_rendered(entry["reason"]), self.body)


class TestItReusesTheClientsStylesheet(unittest.TestCase):
    """The design is the client's, linked, not reimplemented."""

    STYLESHEETS = (
        "/styles/fonts.css",
        "/styles/redesign.css",
        "/styles/grove/press.css",
    )

    def test_the_page_links_the_client_stylesheets(self) -> None:
        body = _page()
        for href in self.STYLESHEETS:
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', body)

    def test_those_stylesheets_are_actually_served(self) -> None:
        for href in self.STYLESHEETS:
            with self.subTest(href=href):
                response = client.get(href)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.headers["content-type"].startswith("text/css"))

    def test_the_self_hosted_fonts_resolve(self) -> None:
        # fonts.css asks for /fonts/*.woff2 by absolute path. A stylesheet that
        # 404s its own faces renders in a fallback and the page stops looking
        # like the product.
        css = client.get("/styles/fonts.css").text
        for face in sorted(set(re.findall(r'url\("(/fonts/[^"]+)"\)', css))):
            with self.subTest(face=face):
                self.assertEqual(client.get(face).status_code, 200)

    def test_the_page_adds_no_stylesheet_of_its_own(self) -> None:
        # The claim is that 10,256 lines of design survive the move untouched.
        # An inline <style> block or a fourth sheet would be that claim
        # quietly failing.
        body = _page()
        self.assertNotIn("<style", body)
        self.assertEqual(len(re.findall(r'rel="stylesheet"', body)), len(self.STYLESHEETS))

    def test_the_page_invents_no_class_of_its_own(self) -> None:
        # The strongest form of "reuses the stylesheet": every class on the
        # Python page is either one press.css styles or one the React shelf
        # already writes. A name that is neither would be this slice quietly
        # starting a second design system.
        body = _page("press_pro")
        css = "\n".join(
            (_REPO / "src" / "styles" / name).read_text(encoding="utf-8")
            for name in ("redesign.css", "grove/press.css")
        )
        # cp-read__idle and cp-read__on carry no rule of their own in either
        # implementation: they are the wrappers whose CHILDREN press.css
        # styles. Read from the JSX rather than listed here, so a rename on
        # the client side surfaces as a failure instead of a stale allowance.
        jsx = (_REPO / "src" / "pages" / "grove" / "PressShelf.jsx").read_text(encoding="utf-8")
        used = {
            token
            for attribute in re.findall(r'class="([^"]+)"', body)
            for token in attribute.split()
        }
        invented = sorted(
            name
            for name in used
            if f".{name}" not in css and f'"{name}' not in jsx and f" {name}" not in jsx
        )
        self.assertEqual(invented, [], "classes neither styled nor used by the client")


class TestTheTierDescribesAndDoesNotGrant(unittest.TestCase):
    """A query string changes the copy. It cannot change what is served."""

    def test_the_standard_plan_is_shown_six_and_locked_out_of_six(self) -> None:
        body = _page("press")
        standard = [d for d in launch.LAUNCH_COLLECTION if d.shelf == "standard"]
        locked = [d for d in launch.LAUNCH_COLLECTION if d.shelf != "standard"]
        self.assertEqual(body.count("cp-badge--act"), len(standard))
        self.assertEqual(body.count("cp-badge--locked"), len(locked))

    def test_an_unknown_tier_falls_back_to_the_cheapest_plan(self) -> None:
        # Not to the most generous, and not to a 422: the value arrives from a
        # query string, and the failure mode worth avoiding is a guessed tier
        # name describing a paid shelf.
        self.assertEqual(shelf.resolve_tier("administrator"), "press")
        self.assertEqual(shelf.resolve_tier(None), "press")
        self.assertEqual(_page("administrator"), _page("press"))

    def test_every_download_on_the_page_points_at_the_authenticated_route(self) -> None:
        body = _page("grove")
        actions = set(re.findall(r'<form method="get" action="([^"]+)"', body))
        self.assertTrue(actions, "the page rendered no downloads at all")
        for action in sorted(actions):
            with self.subTest(action=action):
                self.assertRegex(action, r"^/press/collections/[a-z-]+/download$")

    def test_those_downloads_still_refuse_a_reader_with_no_session(self) -> None:
        # The point of the whole arrangement: the page describes a grove shelf
        # to anyone who asks for one, and the route behind every tile does not
        # care what the page said.
        body = _page("grove")
        for action in sorted(set(re.findall(r'action="(/press/[^"]+)"', body))):
            with self.subTest(action=action):
                self.assertEqual(client.get(action).status_code, 401)

    def test_a_session_outranks_the_query_string(self) -> None:
        signed_in = TestClient(app)
        signed_in.post(
            "/auth/login",
            json={"email": "reader@example.org", "password": "correct-horse"},
        )
        body = signed_in.get("/press/shelf", params={"tier": "grove"}).text
        # The reader's own plan is press, so the page must show the press
        # shelf however the query is dressed.
        self.assertIn("plan press · shelf reach standard", body)
        self.assertNotIn("shelf reach grove", body)
        standard = [d for d in launch.LAUNCH_COLLECTION if d.shelf == "standard"]
        self.assertEqual(body.count("cp-badge--act"), len(standard))


class TestItAgreesWithTheApiItIsServedBeside(unittest.TestCase):
    """The page and the JSON route must not describe two different shelves."""

    def test_the_page_opens_exactly_what_the_collections_route_serves(self) -> None:
        for tier in shelf.KNOWN_TIERS:
            with self.subTest(tier=tier):
                view = shelf.view_for(tier)
                page_open = {
                    entry.id
                    for band in view.bands
                    for entry in band.entries
                    if entry.open
                }
                route_open = {
                    row["id"] for row in repository.collections_for(tier)
                }
                self.assertEqual(page_open, route_open)


class TestTheDriftsThisSliceFound(unittest.TestCase):
    """Two places the two languages disagree today, pinned so a fix is noticed.

    Both assertions are written to fail once the disagreement is settled. Read
    a failure here as "somebody fixed it, delete this test", not as a
    regression.
    """

    def test_python_grants_the_tree_plan_a_shelf_that_javascript_does_not(self) -> None:
        # server/cedar_press/repository.py maps "tree" to the grove shelf.
        # src/features/grove/pressAccess.js has no "tree" key in PLAN_REACH,
        # so shelfReach() returns null and canOpenDataset() is false for every
        # collection. Nothing in either suite compares the two maps.
        self.assertEqual(repository.SHELF_BY_TIER.get("tree"), "grove")
        self.assertTrue(
            all(repository.may_open("tree", d.id) for d in launch.LAUNCH_COLLECTION)
        )
        javascript = (
            _REPO / "src" / "features" / "grove" / "pressAccess.js"
        ).read_text(encoding="utf-8")
        reach = re.search(r"PLAN_REACH = Object\.freeze\(\{(.*?)\}\)", javascript, re.S)
        self.assertIsNotNone(reach, "PLAN_REACH has been rewritten; recheck this by hand")
        self.assertNotIn(
            "tree",
            reach.group(1),
            "pressAccess.js now knows the tree plan: the languages agree, so "
            "delete this test and its entry in docs/PYTHON_FIRST_SITE.md",
        )

    def test_the_python_catalog_snapshot_is_behind_the_javascript_one(self) -> None:
        # press_catalog.CATALOG is regenerated by hand with
        # scripts/dump-press.mjs, and the hand-run step was skipped: `nest` is
        # in the storefront's twelve and in pressCatalog.js, and not in the
        # snapshot Python serves.
        gap = shelf._catalog_gap()
        self.assertEqual(
            list(gap),
            ["nest"],
            "the catalog snapshot has moved: regenerate the measurement in "
            "docs/PYTHON_FIRST_SITE.md, and delete this test if the gap is now empty",
        )

    def test_regenerating_the_snapshot_would_close_that_gap(self) -> None:
        # Proof the gap is a stale dump and not a deliberate omission: run the
        # dump and the entry is there. Nothing is written; the output is read
        # and thrown away.
        dump = _REPO / "scripts" / "dump-press.mjs"
        result = subprocess.run(  # noqa: S603
            ["node", str(dump)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=_REPO,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f"dump-press.mjs exited {result.returncode}: {result.stderr}")
        fresh = {entry["id"] for entry in json.loads(result.stdout)["catalog"]}
        stale = {entry["id"] for entry in press_catalog.CATALOG}
        self.assertEqual(
            fresh - stale,
            {"nest"},
            "the dump no longer explains the gap; the snapshot may have been "
            "regenerated, in which case delete this test",
        )


if __name__ == "__main__":
    unittest.main()
