"""Article authorization is enforced before the content store is read."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import protected_articles
from cedar_press.app import app
from cedar_press.session import Session, current_session


class ProtectedArticleTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.previous = app.dependency_overrides.copy()

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        self.client.close()

    def as_tier(self, tier):
        app.dependency_overrides[current_session] = lambda: (
            Session("reader@example.org", tier) if tier is not None else None
        )

    def test_anonymous_and_other_products_never_read_the_content_store(self):
        for tier in (None, "free", "sprout", "sapling", "grove", "tree", "unknown"):
            self.as_tier(tier)
            with patch.object(protected_articles, "_documents") as read:
                for path in ("/press/articles", "/press/articles/brief-owned"):
                    with self.subTest(tier=tier, path=path):
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 401 if tier is None else 403)
                        self.assertIn("no-store", response.headers["cache-control"])
                        self.assertIn("noindex", response.headers["x-robots-tag"])
                read.assert_not_called()

    def test_press_tiers_receive_metadata_and_requested_body_only(self):
        for tier in ("press", "press_pro"):
            self.as_tier(tier)
            listing = self.client.get("/press/articles")
            self.assertEqual(listing.status_code, 200)
            cards = listing.json()["articles"]
            self.assertTrue(cards)
            self.assertTrue(all("body" not in row and "highlights" not in row for row in cards))
            response = self.client.get("/press/articles/brief-owned")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["article"]["body"])
            self.assertIn(
                "cookie", {value.strip().lower() for value in response.headers["vary"].split(",")}
            )
            self.assertIn("no-store", response.headers["cache-control"])

    def test_unknown_and_external_ids_are_not_bodies(self):
        self.as_tier("press")
        for slug in ("no-such-piece", "brief-funding"):
            response = self.client.get("/press/articles/" + slug)
            self.assertEqual(response.status_code, 404)
            self.assertIn("no-store", response.headers["cache-control"])

    def test_private_editorial_fields_and_local_evidence_paths_never_escape(self):
        record = {
            "id": "fixture",
            "hosted": True,
            "title": "A sourced result",
            "internalReview": {"private": "review-only-secret"},
            "body": [
                {"kind": "p", "text": "Reader text", "internalReview": "review-only-secret"},
                {
                    "kind": "figure",
                    "chart": "bars",
                    "source": "funding",
                    "points": [{"label": "A", "value": 3, "rawPath": "C:/private"}],
                    "sources": [
                        {
                            "title": "Public",
                            "url": "https://example.org/evidence",
                            "internalReview": "review-only-secret",
                        },
                        {"title": "Local", "url": "file:///C:/private"},
                    ],
                },
            ],
            "sources": [
                {"url": "https://example.org/report", "privatePath": "C:/private"},
                {"url": "http://127.0.0.1/private"},
                {"url": "https://reader:secret@example.org/private"},
            ],
        }
        result = protected_articles.reader_article(record, detail=True)
        rendered = json.dumps(result)
        self.assertNotIn("review-only-secret", rendered)
        self.assertNotIn("C:/private", rendered)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(len(result["body"][1]["sources"]), 1)
        self.assertNotIn("rawPath", result["body"][1]["points"][0])

    def test_invalid_blocks_fail_closed(self):
        with self.assertRaises(ValueError):
            protected_articles.reader_article(
                {"id": "a", "body": [{"kind": "html", "text": "<script>"}]}, detail=True
            )

    def test_demonstrations_stay_out_of_the_subscriber_library(self):
        self.assertTrue(
            all(not row.get("demonstration") for row in protected_articles.article_cards())
        )
        self.as_tier("press_pro")
        for slug in ("brief-deals", "brief-contractors", "brief-funding"):
            with self.subTest(slug=slug):
                self.assertIsNone(protected_articles.article_detail(slug))
                self.assertEqual(self.client.get("/press/articles/" + slug).status_code, 404)

    def test_image_sources_and_block_variants_are_projected(self):
        record = {
            "id": "all-blocks",
            "hosted": True,
            "image": "/pitch/example.webp",
            "authors": [{"name": "Editor", "photo": "/photo/editor.webp", "private": "hidden"}],
            "body": [
                {"kind": "h2", "text": "Heading"},
                {"kind": "pull", "text": "A quotation"},
                {"kind": "image", "src": "/pitch/a.webp", "alt": "A"},
                {
                    "kind": "pair",
                    "images": [
                        {"src": "/pitch/a.webp", "alt": "A"},
                        {"src": "https://example.org/b.webp", "alt": "B"},
                    ],
                },
                {
                    "kind": "figure",
                    "chart": "sankey",
                    "source": "funding",
                    "flows": [{"from": "A", "to": "B", "value": 1, "private": "hidden"}],
                },
            ],
        }
        result = protected_articles.reader_article(record, detail=True)
        self.assertEqual(len(result["body"]), 5)
        self.assertNotIn("hidden", json.dumps(result))
        self.assertEqual(result["authors"][0]["photo"], "/photo/editor.webp")

    def test_url_filter_refuses_local_authenticated_or_malformed_addresses(self):
        for value in (
            None,
            3,
            "",
            "file:///tmp/private",
            "C:/private",
            "https://localhost/a",
            "http://10.0.0.1/a",
            "https://example.internal/a",
            "https://example.org/" + "x" * 2050,
            "https://[bad/a",
        ):
            with self.subTest(value=str(value)[:40]):
                self.assertIsNone(protected_articles._public_url(value))
        self.assertIsNone(protected_articles._image_url("/pitch/../private"))
        self.assertEqual(
            protected_articles._public_url("https://example.org/a"),
            "https://example.org/a",
        )

    def test_private_image_paths_and_unknown_series_are_not_accepted(self):
        result = protected_articles.reader_article(
            {
                "id": "private-image",
                "image": "C:/private",
                "href": "file:///private",
                "authors": [{"name": "Editor", "photo": "C:/private"}],
            },
            detail=True,
        )
        self.assertIsNone(result["image"])
        self.assertIsNone(result["href"])
        self.assertNotIn("photo", result["authors"][0])
        with self.assertRaises(ValueError):
            protected_articles.reader_article(
                {
                    "id": "bad-series",
                    "body": [{"kind": "figure", "series": ["__proto__"], "points": []}],
                },
                detail=True,
            )

    def test_duplicate_or_non_slug_article_ids_are_rejected(self):
        for rows in ([{"id": "same"}, {"id": "same"}], [{"id": "../private"}]):
            with patch.object(protected_articles, "_CONTENT") as content:
                content.read_text.return_value = json.dumps(rows)
                with self.assertRaises(ValueError):
                    protected_articles._documents()

    def test_sources_accept_only_named_public_fields(self):
        result = protected_articles._sources(
            [
                None,
                "file:///private",
                {"url": "https://example.org", "title": "Source", "internalReview": "hidden"},
            ]
        )
        self.assertEqual(result, [{"title": "Source", "url": "https://example.org"}])
        self.assertEqual(protected_articles._sources(None), [])

    def test_early_access_card_is_labelled_without_its_review_notes(self):
        result = protected_articles.reader_article(
            {
                "id": "early",
                "earlyAccess": True,
                "internalReview": "hidden",
            }
        )
        self.assertEqual(result["kind"], "Early access")
        self.assertNotIn("internalReview", result)

    def test_paragraph_links_become_public_citations_without_html_interpretation(self):
        record = {
            "kind": "p",
            "text": (
                "The [owners' announcement](https://example.org/news) confirms the deal. "
                "[Local notes](file:///C:/private) stay private. <b>Literal text</b>"
            ),
            "sources": [{"url": "https://example.org/news", "title": "Primary source"}],
        }
        result = protected_articles._block(record)
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["url"], "https://example.org/news")
        self.assertNotIn("file:", result["text"])
        self.assertNotIn("](", result["text"])
        self.assertIn("<b>Literal text</b>", result["text"])
        self.assertIn("owners' announcement", result["text"])

    def test_multiple_valid_links_keep_their_order_and_invalid_links_are_not_clickable(self):
        result = protected_articles._block(
            {
                "kind": "p",
                "text": (
                    "[One](https://example.org/one) and [Two](https://example.org/two) "
                    "and [not a web link](javascript:alert)"
                ),
            }
        )
        self.assertEqual([x["title"] for x in result["citations"]], ["One", "Two"])
        self.assertNotIn("javascript", result["text"])


class EvidenceFigureTests(unittest.TestCase):
    def source(self):
        return {"url": "https://example.org/announcement", "title": "Owner announcement"}

    def figures(self):
        base = {
            "kind": "figure",
            "id": "test-evidence",
            "caption": "Documented roles",
            "source": "Owner announcement",
            "sources": [self.source()],
            "notes": ["Roles as reported on the stated date.", "No ownership share is inferred."],
        }
        return [
            {
                **base,
                "chart": "relationships",
                "relationships": [
                    {
                        "from": "Government",
                        "relationship": "owns",
                        "to": "Enterprise",
                        "asOf": "2020-01-15",
                        "detail": "The announcement names this relationship.",
                        "sources": [self.source()],
                    }
                ],
            },
            {
                **base,
                "chart": "timeline",
                "events": [
                    {
                        "date": "2022-03-14",
                        "title": "Branding announced",
                        "detail": "A branding update does not establish a second acquisition.",
                        "sources": [self.source()],
                    }
                ],
            },
            {
                **base,
                "chart": "evidenceTable",
                "columns": [
                    {"key": "entity", "label": "Organization"},
                    {"key": "role", "label": "Reported role"},
                    {"key": "asOf", "label": "As of"},
                ],
                "rows": [
                    {
                        "entity": "Manager",
                        "role": "Property manager",
                        "asOf": "2022-03-14",
                        "detail": "Management does not establish ownership.",
                        "sources": [self.source()],
                    }
                ],
            },
        ]

    def test_evidence_round_trips_without_numeric_substitutes_or_private_fields(self):
        for figure in self.figures():
            key = {"relationships": "relationships", "timeline": "events", "evidenceTable": "rows"}[
                figure["chart"]
            ]
            figure["internalReview"] = "private-review"
            figure[key][0]["internalReview"] = "private-review"
            figure[key][0]["rawPath"] = "C:/private"
            figure[key][0]["ownershipPercentage"] = 99
            figure[key][0]["sources"].extend(
                [
                    {"url": "file:///C:/private"},
                    {"url": "http://127.0.0.1/private"},
                ]
            )
            result = protected_articles.reader_article({"body": [figure]}, detail=True)["body"][0]
            self.assertEqual(result["id"], figure["id"])
            self.assertEqual(result[key][0]["detail"], figure[key][0]["detail"])
            self.assertEqual(result[key][0]["sources"], [self.source()])
            serialized = json.dumps(result)
            for private in ("private-review", "C:/private", "ownershipPercentage"):
                self.assertNotIn(private, serialized)
            self.assertNotIn("points", result)
            self.assertNotIn("flows", result)

    def test_malformed_or_unsourced_evidence_fails_closed(self):
        cases = []
        for figure in self.figures():
            key = {"relationships": "relationships", "timeline": "events", "evidenceTable": "rows"}[
                figure["chart"]
            ]
            cases.extend(
                [
                    {**figure, key: []},
                    {**figure, key: ["not an observation"]},
                    {**figure, "points": [{"label": "Invented magnitude", "value": 1}]},
                    {**figure, "sources": [{"url": "file:///C:/private"}]},
                    {**figure, key: [{**figure[key][0], "sources": []}]},
                    {**figure, key: [{**figure[key][0], "detail": {"private": "nested"}}]},
                ]
            )
        table = self.figures()[2]
        cases.append({**table, "columns": [{"key": "__proto__", "label": "Bad"}]})
        cases.append({**table, "columns": [table["columns"][0], table["columns"][0]]})
        cases.append({**table, "rows": [{**table["rows"][0], "asOf": "2022-02-30"}]})
        for figure in cases:
            with self.subTest(chart=figure["chart"]), self.assertRaises(ValueError):
                protected_articles.reader_article({"body": [figure]}, detail=True)

    def test_evidence_detail_stays_behind_press_authorization(self):
        record = {
            "id": "evidence-fixture",
            "hosted": True,
            "earlyAccess": True,
            "draft": True,
            "title": "Test evidence",
            "body": self.figures(),
        }
        previous = app.dependency_overrides.copy()
        try:
            with TestClient(app) as client:
                for tier in (None, "grove", "press", "press_pro"):
                    app.dependency_overrides[current_session] = lambda tier=tier: (
                        Session("reader@example.org", tier) if tier else None
                    )
                    with patch.object(
                        protected_articles, "_documents", return_value=[record]
                    ) as read:
                        response = client.get("/press/articles/evidence-fixture")
                        expected = 401 if tier is None else 403 if tier == "grove" else 200
                        self.assertEqual(response.status_code, expected)
                        self.assertIn("no-store", response.headers["cache-control"])
                        self.assertIn("noindex", response.headers["x-robots-tag"])
                        if expected != 200:
                            read.assert_not_called()
                        else:
                            self.assertEqual(len(response.json()["article"]["body"]), 3)
                            self.assertEqual(
                                response.json()["article"]["body"][0]["relationships"][0]["to"],
                                "Enterprise",
                            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
