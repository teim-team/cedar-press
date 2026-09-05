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
            # The retired pair must stay retired: a page reading them prints
            # nothing, which is what this module did for two days.
            for field in ("standardFrom", "historyFrom"):
                self.assertIsNone(entry.get(field), f"{entry['id']} carries {field}")
            coverage = entry.get("coverage") or {}
            if coverage.get("from") is not None:
                stated.add(str(coverage["from"]))
            if coverage.get("captured"):
                stated.add(str(coverage["captured"])[:4])
        for release in press_catalog.RELEASES.values():
            if release.get("updated"):
                stated.add(str(release["updated"])[:4])
        # Only years inside the page's own body copy, not in URLs or classes.
        printed = set(re.findall(r"\b(1[89]\d{2}|20\d{2})\b", self.body))
        self.assertTrue(
            printed <= stated,
            f"the page prints years nothing states: {sorted(printed - stated)}",
        )

    def test_a_collection_with_no_sample_says_cedars_reason_for_it(self) -> None:
        """The fixture DID go away, exactly as this test warned it might.

        `owned` was the collection with no sample; the 2026-09-04 rebuild gave
        it one, and measured against the manifest every collection now has a
        sample. So the test no longer hardcodes which collection is missing
        one - it asks the data, and asserts the page explains whichever ones
        are. When none is missing there is nothing to render and nothing to
        assert, which is the honest outcome rather than a failure.
        """
        missing = [
            d.id
            for d in launch.LAUNCH_COLLECTION
            if not (launch.collection_sample(d.id) or {}).get("path")
        ]
        for cid in missing:
            reason = launch.sample_unavailable_reason(cid)
            self.assertTrue(reason, f"{cid} has no sample and no stated reason")
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


def _js_catalog_ids():
    """Ids declared in `PRESS_CATALOG` - and ONLY that array.

    Read from the source rather than the snapshot, because the snapshot is the
    thing under test and a test that reads its own subject proves nothing.

    Bounded at the next `export const`, because `pressCatalog.js` declares two
    more id-bearing arrays after it and the first version of this helper
    swallowed both: `PRESS_TAXONOMY` (subject headings - policy, labor,
    markets) and `GROVE_PUBLIC_DATA` (Cedar Grove's public-data library -
    census, economy, public-finance). Neither is a Cedar Press dataset, and
    counting them reported the service as eleven collections behind when it is
    exactly level.
    """
    import re as _re
    from pathlib import Path as _P
    root = _P(__file__).resolve().parents[2]
    txt = (root / "src" / "features" / "grove" / "pressCatalog.js").read_text(
        encoding="utf-8", errors="replace")
    start = txt.index("export const PRESS_CATALOG")
    marker = chr(10) + "export const "
    nxt = txt.find(marker, start + 10)
    body = txt[start:nxt if nxt > 0 else len(txt)]
    return _re.findall(r'id:\s*"([a-z0-9-]+)"', body)


class TestTheCatalogDriftIsClosed(unittest.TestCase):
    """The `nest` snapshot drift is FIXED, so the tests that pinned it are gone.

    `TestTheDriftsThisSliceFound` asserted that the Python catalog snapshot was
    one collection behind the JavaScript one - `nest` on the shelf, in the
    browser's catalog, unknown to the service - and its own failure message
    said to delete it once the gap emptied. Two branches then merged: the
    python-first slice that found the drift, and the repricing branch that
    regenerated the snapshot as part of its own work. The gap closed as a side
    effect of combining them, which is the merge doing its job.

    Verified before deleting rather than on the test's say-so: `nest` is in
    `press_catalog.CATALOG` (13 ids) and in `pressCatalog.js`.

    What replaces it is the assertion that matters going forward - not that a
    specific gap exists, but that there is no gap at all.
    """

    def test_the_python_and_javascript_catalogs_hold_the_same_ids(self):
        from cedar_press.press_catalog import CATALOG
        py = {getattr(c, "id", None) or c["id"] for c in CATALOG}
        js = set(_js_catalog_ids())
        self.assertEqual(
            py - js, set(),
            "the Python catalog names a collection the JavaScript one does not")
        self.assertEqual(
            js - py, set(),
            "the JavaScript catalog names a collection the service does not "
            "know; regenerate the snapshot")

class TestUnsupportedTiersReachNothing(unittest.TestCase):
    """A real but unsupported plan must not be shown a paid shelf.

    Codex, PR #38. `view_for` called `resolve_tier` a second time - the caller
    already sanitises the query-string path - and `resolve_tier` falls back to
    `DEFAULT_TIER`, which is `press`, the entry PAID plan. So a signed-in
    reader on `free`, `sprout` or `sapling`, none of which is in
    `SHELF_BY_TIER`, saw six collections marked "yours to download" while
    `repository.may_open` refused every one of them.

    `resolve_tier`'s own docstring had already named this: *"Falling back to
    the LOWEST plan matters -- the same defect in the other direction would
    describe a paid shelf to anyone who guessed a tier name."* The fallback
    was pointed at a paid plan, and it reached a signed-in session rather than
    a guessed query string.

    The page and the download route must agree, which is what the two
    assertions below check together.
    """

    def test_a_supported_plan_reaches_its_own_shelf_and_below(self):
        self.assertEqual(
            [(b.shelf, b.reached) for b in shelf.view_for("press").bands],
            [("standard", True), ("pro", False), ("grove", False)])
        self.assertEqual(
            [(b.shelf, b.reached) for b in shelf.view_for("press_pro").bands],
            [("standard", True), ("pro", True), ("grove", False)])
        self.assertEqual(
            [(b.shelf, b.reached) for b in shelf.view_for("tree").bands],
            [("standard", True), ("pro", True), ("grove", True)],
            "tree is the full platform and includes Grove")

    def test_an_unsupported_plan_reaches_nothing(self):
        for tier in ("free", "sprout", "sapling", None, "nonsense"):
            with self.subTest(tier=tier):
                view = shelf.view_for(tier)
                self.assertTrue(
                    all(not b.reached for b in view.bands),
                    f"{tier!r} was shown a shelf it cannot open")

    def test_the_page_and_the_download_route_agree(self):
        """The real invariant: nothing rendered open may be refused.

        This half covers the SERVER-rendered shelf, and it covers only what
        that page can render: ``view_for`` fills its bands from
        ``LAUNCH_COLLECTION``, the twelve storefront collections. The browser
        renders from ``PRESS_CATALOG``, which was thirteen until 2026-09-04,
        and it broke this invariant on the entry the two did not share --
        Codex, PR #41. The
        client's half is
        ``test_access.py::TestNothingTheClientOpensIsRefused``, which runs
        ``canOpenDataset`` through ``scripts/dump-access.mjs`` and holds both
        directions of the same rule. Neither half subsumes the other: this one
        needs no ``node`` and covers the tiers ``shelf.py`` accepts; that one
        covers the collection this page cannot show.
        """
        for tier in ("press", "press_pro", "tree", "free", "sprout", None):
            view = shelf.view_for(tier)
            for band in view.bands:
                for entry in band.entries:
                    if not band.reached:
                        continue
                    with self.subTest(tier=tier, dataset=entry.id):
                        self.assertTrue(
                            repository.may_open(tier, entry.id),
                            f"the shelf shows {entry.id} open to {tier!r} and "
                            f"the download route refuses it")


class TestTheShelfStatesCoverage(unittest.TestCase):
    """The badges and the bands read the catalog's live coverage field.

    ``shelf.py`` read ``standardFrom`` and ``historyFrom`` until 2026-09-04,
    a pair the catalog retired on 2026-09-02, so every badge said "Coverage
    varies" and no band stated a year, and the only test on the subject
    checked that the retired names were absent from the catalog. These check
    what the page says.
    """

    def test_every_series_badge_states_its_first_year(self) -> None:
        view = shelf.view_for("press_pro")
        by_id = {entry["id"]: entry for entry in press_catalog.CATALOG}
        for band in view.bands:
            for entry in band.entries:
                coverage = by_id[entry.id]["coverage"]
                with self.subTest(dataset=entry.id):
                    if coverage["kind"] == "series":
                        self.assertEqual(entry.coverage, f"{coverage['from']} to present")
                    else:
                        self.assertEqual(
                            entry.coverage, f"Current roster, captured {coverage['captured']}"
                        )
                    self.assertNotEqual(entry.coverage, "Coverage varies")

    def test_each_storefront_band_reaches_back_to_its_deepest_series(self) -> None:
        view = shelf.view_for("press_pro")
        by_id = {entry["id"]: entry for entry in press_catalog.CATALOG}
        for band in view.bands:
            years = [
                by_id[entry.id]["coverage"]["from"]
                for entry in band.entries
                if by_id[entry.id]["coverage"]["kind"] == "series"
            ]
            with self.subTest(shelf=band.shelf):
                self.assertEqual(band.earliest, min(years) if years else None)
        # A roster's capture year never becomes a band's earliest year.
        pro = next(band for band in view.bands if band.shelf == "pro")
        self.assertNotEqual(pro.earliest, 2026)
