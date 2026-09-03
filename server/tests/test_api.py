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
os.environ["CEDAR_PRESS_CODES"] = json.dumps(
    {
        "TBN4-9K2M-X7QD": {"email": "new@example.org", "tier": "press"},
        "TBN4-9K2M-X7QE": {"email": "upgrade@example.org", "tier": "press_pro"},
        "TBN4-0000-EXPD": {
            "email": "late@example.org",
            "tier": "press",
            "expires": "2020-01-01",
        },
        # Issued to an address that already has an account.
        "TBN4-0000-DUPE": {"email": "reader@example.org", "tier": "press"},
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from cedar_press import (
    codes,  # noqa: E402
    press_catalog,  # noqa: E402
    ratelimit,  # noqa: E402
)
from cedar_press import session as session_module  # noqa: E402
from cedar_press.app import app  # noqa: E402

client = TestClient(app)


def sign_in(email: str = "reader@example.org", password: str = "correct-horse"):
    return client.post("/auth/login", json={"email": email, "password": password})


class TestSession(unittest.TestCase):
    def setUp(self) -> None:
        client.cookies.clear()
        ratelimit.reset_for_tests()

    def test_health_needs_no_session(self) -> None:
        self.assertEqual(client.get("/health").status_code, 200)

    def test_reading_without_a_session_is_refused(self) -> None:
        for path in ("/me", "/press/collections", "/press/articles"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 401)

    def test_a_wrong_password_is_refused(self) -> None:
        response = sign_in(password="wrong")
        self.assertEqual(response.status_code, 401)
        # Flat, not nested under `detail`. This asserted the nested shape and
        # so pinned the bug in place: the client reads `code` off the top
        # level, so every worded refusal was reaching the reader as
        # "Request failed (401)." and the test called that correct.
        self.assertEqual(response.json()["code"], "INVALID_CREDENTIALS")

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
        # Every test here signs in; without a reset the class's own logins
        # exhaust the per-client allowance partway through and later tests
        # fail with 429s that have nothing to do with the catalog.
        ratelimit.reset_for_tests()
        sign_in()

    def test_collections_carry_what_the_shelf_reads(self) -> None:
        payload = client.get("/press/collections").json()["collections"]
        self.assertTrue(payload)
        for key in ("id", "name", "version", "vintage", "updated"):
            self.assertIn(key, payload[0])

    def test_articles_are_served(self) -> None:
        self.assertTrue(client.get("/press/articles").json()["articles"])

    def test_a_download_carries_its_citation(self) -> None:
        response = client.get("/press/collections/deals/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("cite_as", response.text)

    def test_an_unknown_collection_is_not_found(self) -> None:
        self.assertEqual(client.get("/press/collections/nope/download").status_code, 403)

    def test_cedar_answers_from_a_collection_profile(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "How was this collection constructed?", "collectionId": "deals"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("resolved", payload["answer"])
        self.assertIn("Deals", payload["basis"])

    def test_cedar_flags_demonstration_statistics(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "What are the headline figures?", "collectionId": "deals"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("demonstration", response.json()["answer"])

    def test_cedar_labels_real_statistics_with_their_source(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "What are the headline figures?", "collectionId": "owned"},
        )
        self.assertEqual(response.status_code, 200)
        answer = response.json()["answer"]
        self.assertNotIn("demonstration", answer)
        self.assertIn("Source:", answer)

    def test_how_many_routes_to_statistics_not_construction(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "How many records are in this collection?", "collectionId": "deals"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("currently holds", response.json()["answer"])

    def test_a_two_series_figure_answers_with_both_series(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "What are the headline figures?", "collectionId": "funding"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison", response.json()["answer"])

    def test_cedar_still_refuses_what_it_cannot_support(self) -> None:
        response = client.post("/cedar/ask", json={"question": "what?"})
        self.assertEqual(response.status_code, 501)
        response = client.post(
            "/cedar/ask",
            json={
                "question": "List every contract Cherokee Nation received.",
                "collectionId": "contractors",
            },
        )
        self.assertEqual(response.status_code, 501)

    def test_a_collection_profile_is_served(self) -> None:
        response = client.get("/press/collections/owned/profile")
        self.assertEqual(response.status_code, 200)
        profile = response.json()
        self.assertEqual(profile["collection_id"], "owned")
        self.assertFalse(profile["demonstration"])
        self.assertEqual(client.get("/press/collections/nope/profile").status_code, 404)

    def test_a_catalog_collection_answers_from_its_catalog_entry(self) -> None:
        # Gaming is the catalog-only collection: it sits on the Grove shelf and
        # the storefront's twelve do not include it, so it has no descriptor
        # and its profile comes from the catalog. This test asked about
        # lobbying until lobbying became one of the twelve with a real
        # descriptor behind it; the subject moved, the invariant did not.
        response = client.post(
            "/cedar/ask",
            json={"question": "What does this collection cover?", "collectionId": "gaming"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        # Compared against the catalog's own blurb rather than a word the
        # answer is expected to contain: the previous subject happened to
        # repeat its own name in its blurb and gaming's does not, which would
        # make this a test of the copy rather than of where the copy came from.
        entry = next(c for c in press_catalog.CATALOG if c["id"] == "gaming")
        self.assertIn(entry["blurb"], payload["answer"])
        self.assertIn("catalog entry", payload["basis"])

    def test_a_shipping_collection_answers_from_its_descriptor(self) -> None:
        # The other half of the pair, and the one that changed: lobbying now
        # carries Cedar's measured descriptor, so its basis names a version
        # rather than the catalog. No vintage is stated by any collection, so
        # the basis must not print one.
        response = client.post(
            "/cedar/ask",
            json={"question": "What does this collection cover?", "collectionId": "lobbying"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("catalog entry", payload["basis"])
        self.assertIn("v0", payload["basis"])
        self.assertNotIn("vintage", payload["basis"])

    def test_coverage_is_the_same_sentence_for_every_tier(self) -> None:
        # This test changed subject on 2026-09-02. It used to check that the
        # coverage sentence was PHRASED for the asking tier, because Cedar
        # Press opened lobbying from 2010 and Cedar Press+ opened the archive
        # behind it, so the same question had two right answers. The year cap
        # is retired: coverage is a fact about the collection, and a sentence
        # that still varied by plan would be the old ladder surviving in the
        # copy. So the check is now that the two readers hear the same thing.
        question = {
            "question": "What does this collection cover?",
            "collectionId": "lobbying",
        }
        ratelimit.reset_for_tests()
        sign_in("pro@example.org")
        pro = client.post("/cedar/ask", json=question)
        self.assertEqual(pro.status_code, 200)
        ratelimit.reset_for_tests()
        sign_in()
        standard = client.post("/cedar/ask", json=question)
        self.assertEqual(standard.status_code, 200)

        answer = standard.json()["answer"]
        self.assertEqual(pro.json()["answer"], answer)
        # And it says one year, not a window and a depth. The year is the
        # catalog's measured one rather than a literal here, so re-measuring
        # a collection does not have to be re-typed into a test.
        entry = next(c for c in press_catalog.CATALOG if c["id"] == "lobbying")
        self.assertIn(f"Coverage from {entry['coverage']['from']} to present.", answer)
        self.assertNotIn("Cedar Press+ opens", answer)
        self.assertNotIn("full reconstructed archive", answer)
        ratelimit.reset_for_tests()

    def test_a_catalog_collection_says_it_has_no_figures(self) -> None:
        # A quantity question about an unreleased collection is answered with
        # the honest state of the numbers, never a routing miss or a made-up
        # figure.
        response = client.post(
            "/cedar/ask",
            json={"question": "How many records are in it?", "collectionId": "gaming"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("no published figures", response.json()["answer"])

    def test_a_shipping_collection_without_a_figure_says_so_too(self) -> None:
        # Eight of the twelve have real row counts and no figure series, which
        # is a different state from "no release yet" and must not be answered
        # with a number pulled from the row count. Cedar publishes no figures
        # for them, so the answer says exactly that.
        response = client.post(
            "/cedar/ask",
            json={"question": "How many records are in it?", "collectionId": "lobbying"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("no published figures", response.json()["answer"])

    def test_cedar_answers_what_a_release_changed(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={
                "question": "What changed in Federal Funding v4.1?",
                "collectionId": "funding",
            },
        )
        self.assertEqual(response.status_code, 200)
        answer = response.json()["answer"]
        # The named release, not the latest one, and flagged as the
        # demonstration content it is.
        self.assertIn("v4.1", answer)
        self.assertIn("412", answer)
        self.assertIn("demonstration", answer)

    def test_a_change_question_without_a_version_gets_the_latest(self) -> None:
        response = client.post(
            "/cedar/ask",
            json={"question": "What changed in the latest release?", "collectionId": "deals"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("v9.0", response.json()["answer"])

    def test_releases_are_served_from_the_dumped_history(self) -> None:
        response = client.get("/press/releases")
        self.assertEqual(response.status_code, 200)
        rows = response.json()["releases"]
        self.assertTrue(rows)
        # Most recently updated first, and each row names its collection.
        dates = [row["updated"] for row in rows]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertIn("funding", {row["id"] for row in rows})

    def test_a_catalog_collection_profile_is_served(self) -> None:
        # Gaming, for the same reason as above: it is the collection the
        # catalog carries and the storefront does not sell, so every
        # release-shaped field is None.
        response = client.get("/press/collections/gaming/profile")
        self.assertEqual(response.status_code, 200)
        profile = response.json()
        self.assertEqual(profile["collection_id"], "gaming")
        self.assertIsNone(profile["version"])
        self.assertIsNone(profile["headline_statistics"])


class TestEntitlement(unittest.TestCase):
    def test_a_download_is_refused_without_a_session(self) -> None:
        client.cookies.clear()
        self.assertEqual(client.get("/press/collections/deals/download").status_code, 401)


class TestErrorShape(unittest.TestCase):
    """`{code, message}` at the top level, which is what `src/api.js` reads.

    FastAPI wraps `detail`, so without the handler every worded refusal
    arrives at the reader as "Request failed (401)."
    """

    def test_a_refusal_carries_its_code_at_the_top_level(self) -> None:
        response = client.post(
            "/auth/login", json={"email": "reader@example.org", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "INVALID_CREDENTIALS")
        self.assertIn("Cedar Press confirmation", response.json()["message"])

    def test_an_ordinary_404_is_left_alone(self) -> None:
        # Only dict details with a code are flattened; everything else keeps
        # FastAPI's shape so nothing else in the stack has to care.
        response = client.get("/press/articles/nope")
        self.assertEqual(response.status_code, 404)


class TestActivation(unittest.TestCase):
    """The way in: a code from Tribal Business News, then an account."""

    def setUp(self) -> None:
        client.cookies.clear()
        codes.reset_for_tests()
        ratelimit.reset_for_tests()
        session_module.forget_activated_for_tests()

    def test_a_good_code_validates_without_creating_anything(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-9K2M-X7QD", "email": "new@example.org"},
        )
        self.assertEqual(response.status_code, 204)
        # Nothing was created, so the code is still spendable and the address
        # still has no account.
        self.assertFalse(session_module.account_exists("new@example.org"))

    def test_hyphens_and_case_are_the_readers_problem_not_theirs(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "  tbn49k2m x7qd ", "email": "New@Example.org"},
        )
        self.assertEqual(response.status_code, 204)

    def test_an_unissued_code_is_refused(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-0000-0000", "email": "new@example.org"},
        )
        self.assertEqual(response.json()["code"], "PRESS_CODE_INVALID")

    def test_a_code_issued_to_another_address_is_refused(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-9K2M-X7QD", "email": "someone@example.org"},
        )
        self.assertEqual(response.json()["code"], "PRESS_CODE_EMAIL_MISMATCH")

    def test_an_expired_code_says_so(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-0000-EXPD", "email": "late@example.org"},
        )
        self.assertEqual(response.json()["code"], "PRESS_CODE_EXPIRED")

    def test_an_address_that_already_has_an_account_is_sent_to_sign_in(self) -> None:
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-0000-DUPE", "email": "reader@example.org"},
        )
        self.assertEqual(response.json()["code"], "EMAIL_IN_USE")

    def test_activation_creates_the_account_and_signs_them_in(self) -> None:
        response = client.post(
            "/press/activation",
            json={
                "code": "TBN4-9K2M-X7QD",
                "email": "new@example.org",
                "password": "a-long-enough-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "new@example.org")
        # Signed in already: the client calls refreshSession() straight after.
        self.assertEqual(client.get("/me").status_code, 200)

    def test_the_tier_comes_off_the_code_not_the_request(self) -> None:
        client.post(
            "/press/activation",
            json={
                "code": "TBN4-9K2M-X7QE",
                "email": "upgrade@example.org",
                "password": "a-long-enough-password",
            },
        )
        self.assertEqual(client.get("/me").json()["workspace_tier"], "press_pro")

    def test_a_code_activates_once(self) -> None:
        first = client.post(
            "/press/activation",
            json={
                "code": "TBN4-9K2M-X7QD",
                "email": "new@example.org",
                "password": "a-long-enough-password",
            },
        )
        self.assertEqual(first.status_code, 200)
        second = client.post(
            "/press/activation",
            json={
                "code": "TBN4-9K2M-X7QD",
                "email": "new@example.org",
                "password": "another-long-password",
            },
        )
        self.assertEqual(second.json()["code"], "PRESS_CODE_USED")

    def test_the_new_account_can_sign_in_afterwards(self) -> None:
        client.post(
            "/press/activation",
            json={
                "code": "TBN4-9K2M-X7QD",
                "email": "new@example.org",
                "password": "a-long-enough-password",
            },
        )
        client.cookies.clear()
        response = sign_in("new@example.org", "a-long-enough-password")
        self.assertEqual(response.status_code, 200)

    def test_a_short_password_is_refused_and_the_code_survives(self) -> None:
        response = client.post(
            "/press/activation",
            json={"code": "TBN4-9K2M-X7QD", "email": "new@example.org", "password": "short"},
        )
        self.assertEqual(response.json()["code"], "PASSWORD_TOO_SHORT")
        # The code must not be spent by a failed attempt: a subscriber who
        # typed a weak password has not lost their membership.
        again = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-9K2M-X7QD", "email": "new@example.org"},
        )
        self.assertEqual(again.status_code, 204)

    def test_activation_is_re_checked_rather_than_trusted_from_step_one(self) -> None:
        # Step one sets no state, so step two must stand on its own. Calling
        # it with a code that was never validated is the same as calling it
        # with one that was: both are checked here.
        response = client.post(
            "/press/activation",
            json={
                "code": "TBN4-0000-0000",
                "email": "new@example.org",
                "password": "a-long-enough-password",
            },
        )
        self.assertEqual(response.json()["code"], "PRESS_CODE_INVALID")


class TestRateLimiting(unittest.TestCase):
    """The control that turns "guessable given enough attempts" into "not".

    An access code is 8 to 32 alphanumeric characters and the activation
    routes say plainly whether one is real. Unlimited, that is an oracle.
    """

    def setUp(self) -> None:
        client.cookies.clear()
        ratelimit.reset_for_tests()
        codes.reset_for_tests()

    def tearDown(self) -> None:
        ratelimit.reset_for_tests()

    def test_guessing_codes_runs_out_of_attempts(self) -> None:
        seen = set()
        for _ in range(ratelimit.ACTIVATION_ATTEMPTS + 4):
            response = client.post(
                "/press/activation/validate",
                json={"code": "TBN4-0000-0000", "email": "guess@example.org"},
            )
            seen.add(response.status_code)
        self.assertIn(429, seen)

    def test_the_refusal_says_when_to_come_back(self) -> None:
        for _ in range(ratelimit.ACTIVATION_ATTEMPTS + 1):
            response = client.post(
                "/press/activation/validate",
                json={"code": "TBN4-0000-0000", "email": "guess@example.org"},
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "TOO_MANY_ATTEMPTS")
        self.assertGreater(int(response.headers["retry-after"]), 0)

    def test_guessing_passwords_runs_out_of_attempts(self) -> None:
        seen = set()
        for _ in range(ratelimit.LOGIN_ATTEMPTS + 4):
            seen.add(sign_in(password="wrong").status_code)
        self.assertIn(429, seen)

    def test_the_two_surfaces_have_separate_allowances(self) -> None:
        # Failing sign-in must not lock a subscriber out of activation: those
        # are different tasks and doing the second after failing the first is
        # exactly what someone with a new code would do.
        for _ in range(ratelimit.LOGIN_ATTEMPTS + 2):
            sign_in(password="wrong")
        response = client.post(
            "/press/activation/validate",
            json={"code": "TBN4-9K2M-X7QD", "email": "new@example.org"},
        )
        self.assertEqual(response.status_code, 204)

    def test_a_forwarded_header_is_ignored_unless_the_deployment_trusts_it(self) -> None:
        # Otherwise a header the caller controls becomes the identity they are
        # limited by, which is a free reset on every request.
        self.assertNotEqual(os.environ.get("CEDAR_PRESS_TRUST_PROXY"), "1")
        seen = set()
        for i in range(ratelimit.LOGIN_ATTEMPTS + 4):
            seen.add(
                client.post(
                    "/auth/login",
                    json={"email": "reader@example.org", "password": "wrong"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"},
                ).status_code
            )
        self.assertIn(429, seen)

    def test_reading_is_not_rate_limited(self) -> None:
        # The limit is on guessing a secret, not on using the service.
        ratelimit.reset_for_tests()
        self.assertEqual(sign_in().status_code, 200)
        for _ in range(30):
            self.assertEqual(client.get("/press/collections").status_code, 200)


if __name__ == "__main__":
    unittest.main()
