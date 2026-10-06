"""Who a rate limit is counting: the client address behind trusted proxies.

The limiter is only as strong as the identity it keys on. These tests hold
``ratelimit.client_key`` to two properties at once, because each failure mode
is the other's overcorrection:

- a caller cannot choose their own identity by sending ``X-Forwarded-For``
  (the left-most entry is theirs to write, so reading it is a free reset);
- distinct subscribers behind the deployment's proxy are not merged into the
  proxy's own address (one shared allowance is a global lockout).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from starlette.requests import Request  # noqa: E402

from cedar_press import ratelimit  # noqa: E402

CLOUDFRONT = "130.176.0.10"


def request(*forwarded: str, peer: str = CLOUDFRONT) -> Request:
    """A request as the API receives it: one socket peer, any number of XFF headers."""
    headers = [(b"x-forwarded-for", value.encode("latin-1")) for value in forwarded]
    return Request({"type": "http", "headers": headers, "client": (peer, 443)})


def env(trust: str | None = None, hops: str | None = None) -> mock._patch:
    values = {"CEDAR_PRESS_TRUST_PROXY": trust or "", "CEDAR_PRESS_PROXY_HOPS": hops or ""}
    return mock.patch.dict(os.environ, values)


class TestClientIdentity(unittest.TestCase):
    def test_untrusted_deployment_keys_by_the_socket_peer(self) -> None:
        with env():
            self.assertEqual(ratelimit.client_key(request("203.0.113.9")), CLOUDFRONT)

    def test_a_spoofed_left_entry_is_not_the_identity(self) -> None:
        # CloudFront appends the address it saw; whatever the caller sent sits
        # to the left of it.
        with env("1"):
            for spoof in ("10.0.0.1", "10.0.0.2", "garbage", "1.1.1.1, 2.2.2.2"):
                with self.subTest(spoof=spoof):
                    key = ratelimit.client_key(request(f"{spoof}, 198.51.100.7"))
                    self.assertEqual(key, "198.51.100.7")

    def test_a_second_header_sent_ahead_of_the_proxy_does_not_help(self) -> None:
        with env("1"):
            key = ratelimit.client_key(request("10.9.9.9", "198.51.100.7"))
        self.assertEqual(key, "198.51.100.7")

    def test_distinct_clients_behind_the_proxy_stay_distinct(self) -> None:
        with env("1"):
            first = ratelimit.client_key(request("198.51.100.7"))
            second = ratelimit.client_key(request("198.51.100.8"))
        self.assertEqual(first, "198.51.100.7")
        self.assertEqual(second, "198.51.100.8")

    def test_two_hops_take_the_entry_the_outer_proxy_wrote(self) -> None:
        # Caller -> CloudFront -> load balancer -> API. The balancer appends
        # CloudFront's address, CloudFront appended the caller's.
        with env("1", "2"):
            key = ratelimit.client_key(request(f"10.0.0.1, 198.51.100.7, {CLOUDFRONT}"))
        self.assertEqual(key, "198.51.100.7")

    def test_too_few_entries_for_the_chain_falls_back_to_the_peer(self) -> None:
        # Fewer entries than proxies: the request skipped part of the chain,
        # so nothing in its header was written by a proxy we trust.
        with env("1", "2"):
            self.assertEqual(ratelimit.client_key(request("10.0.0.1")), CLOUDFRONT)
        with env("1"):
            self.assertEqual(ratelimit.client_key(request()), CLOUDFRONT)

    def test_a_non_address_where_the_proxy_writes_falls_back_to_the_peer(self) -> None:
        with env("1"):
            self.assertEqual(ratelimit.client_key(request("not-an-ip")), CLOUDFRONT)

    def test_ipv6_callers_share_an_allowance_per_64(self) -> None:
        with env("1"):
            first = ratelimit.client_key(request("2001:db8:1:2::1"))
            second = ratelimit.client_key(request("2001:db8:1:2:ffff::9"))
            other = ratelimit.client_key(request("2001:db8:1:3::1"))
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_unreadable_settings_are_refused_not_guessed(self) -> None:
        for trust, hops in (("yes", None), ("1", "0"), ("1", "-1"), ("1", "two"), ("1", "99")):
            with self.subTest(trust=trust, hops=hops), env(trust, hops):
                with self.assertRaises(ratelimit.ProxyConfigurationError):
                    ratelimit.client_key(request("198.51.100.7"))
                self.assertIsNotNone(ratelimit.configuration_error(require_explicit=False))

    def test_production_must_say_whether_it_sits_behind_a_proxy(self) -> None:
        with env():
            self.assertIsNotNone(ratelimit.configuration_error(require_explicit=True))
            self.assertIsNone(ratelimit.configuration_error(require_explicit=False))
        for trust in ("0", "1"):
            with self.subTest(trust=trust), env(trust):
                self.assertIsNone(ratelimit.configuration_error(require_explicit=True))


if __name__ == "__main__":
    unittest.main()
