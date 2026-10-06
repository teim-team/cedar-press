"""Responses are gzip-compressed for a client that accepts it.

The app added only CORS, so every JSON answer went out at full size:
``/press/collections`` was 48 kB on the wire (2026-10-04 audit). These hold
the middleware in place and check it changes the encoding, never the content.
"""

from __future__ import annotations

import gzip
import unittest

from tests.test_api import client, ratelimit, sign_in


class TestCompression(unittest.TestCase):
    def setUp(self) -> None:
        client.cookies.clear()
        ratelimit.reset_for_tests()
        self.assertEqual(sign_in(email="pro@example.org").status_code, 200)

    def _raw(self, path: str, encoding: str) -> tuple[dict, bytes]:
        with client.stream("GET", path, headers={"Accept-Encoding": encoding}) as response:
            self.assertEqual(response.status_code, 200)
            return dict(response.headers), b"".join(response.iter_raw())

    def test_the_catalog_is_gzipped_when_the_client_accepts_it(self) -> None:
        headers, raw = self._raw("/press/collections", "gzip, deflate, br")
        self.assertEqual(headers.get("content-encoding"), "gzip")
        self.assertIn("accept-encoding", headers.get("vary", "").lower())
        plain_headers, plain = self._raw("/press/collections", "identity")
        self.assertNotIn("content-encoding", plain_headers)
        # Same document, a fraction of the bytes.
        self.assertEqual(gzip.decompress(raw), plain)
        self.assertLess(len(raw), len(plain) / 4, (len(raw), len(plain)))

    def test_a_small_answer_is_left_alone(self) -> None:
        headers, raw = self._raw("/health", "gzip")
        self.assertLess(len(raw), 1000)
        self.assertNotIn("content-encoding", headers)

    def test_a_collection_download_decodes_to_the_same_file(self) -> None:
        path = "/press/collections/funding/download"
        headers, raw = self._raw(path, "gzip")
        _, plain = self._raw(path, "identity")
        self.assertEqual(headers.get("content-encoding"), "gzip")
        self.assertIn("attachment", headers.get("content-disposition", ""))
        self.assertEqual(gzip.decompress(raw), plain)


if __name__ == "__main__":
    unittest.main()
