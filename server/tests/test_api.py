"""The API's contract, from the client's side of it."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["CEDAR_PRESS_SECRET"] = "test-secret"
os.environ["CEDAR_PRESS_INSECURE_COOKIE"] = "1"
os.environ["CEDAR_PRESS_ACCOUNTS"] = json.dumps(
    {
        "reader@example.org": {"password": "correct-horse", "tier": "press"},
        "pro@example.org": {"password": "correct-horse", "tier": "press_pro"},
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from cedar_press.app import app  # noqa: E402

client = TestClient(app)


def sign_in(email: str = "reader@example.org", password: str = "correct-horse"):
    return client.post("/auth/login", json={"email": email, "password": password})


class TestSession(unittest.TestCase):
    def setUp(self) -> None:
        client.cookies.clear()

    def test_health_needs_no_session(self) -> None:
        self.assertEqual(client.get("/health").status_code, 200)

    def test_reading_without_a_session_is_refused(self) -> None:
        for path in ("/me", "/press/collections", "/press/articles"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 401)

    def test_a_wrong_password_is_refused(self) -> None:
        response = sign_in(password="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_CREDENTIALS")

    def test_an_unknown_address_is_refused(self) -> None:
        self.assertEqual(sign_in(email="nobody@example.org").status_code, 401)

    def test_signing_in_returns_the_tier_the_client_resolves_from(self) -> None:
        payload = sign_in().json()
        self.assertEqual(payload["workspace_tier"], "press")
        self.assertEqual(payload["email"], "reader@example.org")

    def test_the_session_cookie_is_http_only(self) -> None:
        response = sign_in()
        header = response.headers["set-cookie"]
        self.assertIn("HttpOnly", header)

    def test_a_forged_cookie_is_refused(self) -> None:
        client.cookies.set("cedar_press_session", "eyJlbWFpbCI6ICJhQGIuYyJ9.not-a-signature")
        self.assertEqual(client.get("/me").status_code, 401)

    def test_signing_out_ends_the_session(self) -> None:
        sign_in()
        self.assertEqual(client.get("/me").status_code, 200)
        self.assertEqual(client.post("/auth/logout").status_code, 204)
        client.cookies.clear()
        self.assertEqual(client.get("/me").status_code, 401)


class TestCatalog(unittest.TestCase):
    def setUp(self) -> None:
        client.cookies.clear()
        sign_in()

    def test_collections_carry_what_the_shelf_reads(self) -> None:
        payload = client.get("/press/collections").json()["collections"]
        self.assertTrue(payload)
        for key in ("id", "name", "version", "vintage", "updated"):
            self.assertIn(key, payload[0])

    def test_articles_are_served(self) -> None:
        self.assertTrue(client.get("/press/articles").json()["articles"])

    def test_releases_are_empty_rather_than_invented(self) -> None:
        self.assertEqual(client.get("/press/releases").json()["releases"], [])

    def test_a_download_carries_its_citation(self) -> None:
        response = client.get("/press/collections/deals/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("cite_as", response.text)

    def test_an_unknown_collection_is_not_found(self) -> None:
        self.assertEqual(client.get("/press/collections/nope/download").status_code, 403)

    def test_cedar_admits_it_is_not_wired(self) -> None:
        response = client.post("/cedar/ask", json={"question": "what?"})
        self.assertEqual(response.status_code, 501)


class TestEntitlement(unittest.TestCase):
    def test_a_download_is_refused_without_a_session(self) -> None:
        client.cookies.clear()
        self.assertEqual(client.get("/press/collections/deals/download").status_code, 401)


if __name__ == "__main__":
    unittest.main()
