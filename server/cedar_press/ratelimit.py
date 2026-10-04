"""Rate limiting on the ways in.

WHY THIS EXISTS
An access code is 8 to 32 alphanumeric characters, and an activation route
says yes to the right code with the right address. Without a limit that is
still a search: an attacker with a script asks it a few million times and
activates somebody else's subscription. (``codes.py`` answers "not
recognized" until code and address both match, so one attempt reveals no
more than that.) The same applies to sign-in, where the guessable secret
is a password rather than a code.

Rate limiting is what turns "guessable given enough attempts" into "not
guessable", and it is the only control here that does that. The careful error
ordering in ``codes.py`` narrows what a single attempt reveals; this is what
bounds how many attempts there are.

WHAT THIS IS NOT
Per-process and in-memory, so several workers each get their own allowance
and a restart forgets everything. That is a real weakening and it is the
seam: in production this is Redis, keyed the same way, and nothing above it
changes. It is not a defence against a distributed attack from many
addresses either — that needs the edge, not the application.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
from collections import defaultdict, deque
from time import monotonic

logger = logging.getLogger(__name__)

#: Attempts allowed per window, per key. Deliberately low: a subscriber types
#: their code once off a confirmation email and their password a few times at
#: worst, so a limit generous enough for a person is still nowhere near
#: enough for a search.
LOGIN_ATTEMPTS = 10
ACTIVATION_ATTEMPTS = 8
WINDOW_SECONDS = 15 * 60

#: Stop the table growing without bound when the callers are all different.
_MAX_KEYS = 10_000

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _prune(seen: deque[float], now: float, window: float) -> None:
    while seen and now - seen[0] > window:
        seen.popleft()


def allow(key: str, *, attempts: int, window: float = WINDOW_SECONDS) -> bool:
    """Whether this key may try again.

    A sliding window rather than a fixed one: a fixed window lets an attacker
    spend the whole allowance at the end of one and the whole of the next
    immediately after, which is twice the intended rate at the boundary.
    """
    now = monotonic()
    with _lock:
        if len(_hits) > _MAX_KEYS:
            # Drop whatever has gone quiet rather than evicting at random,
            # which would forgive whoever is currently being limited.
            for stale in [k for k, v in _hits.items() if not v or now - v[-1] > window]:
                del _hits[stale]
        seen = _hits[key]
        _prune(seen, now, window)
        if len(seen) >= attempts:
            return False
        seen.append(now)
        return True


def retry_after(key: str, *, window: float = WINDOW_SECONDS) -> int:
    """Seconds until this key's oldest attempt falls out of the window."""
    with _lock:
        seen = _hits.get(key)
        if not seen:
            return 0
        return max(1, int(window - (monotonic() - seen[0])))


#: How many proxies sit in front of the API and append to ``X-Forwarded-For``
#: when ``CEDAR_PRESS_TRUST_PROXY=1``. The documented deployment
#: (``docs/HOSTNAMES.md``) is CloudFront in front of the API origin: one hop.
#: A load balancer between CloudFront and the service is a second hop, and
#: ``CEDAR_PRESS_PROXY_HOPS=2`` says so.
DEFAULT_PROXY_HOPS = 1
_MAX_PROXY_HOPS = 10

#: IPv6 callers are limited per /64, the smallest block a single subscriber
#: line is normally assigned. Keying on the full address would hand anyone
#: with one connection 2**64 fresh allowances.
_IPV6_PREFIX = 64

_warned_untrusted_forwarding = False


class ProxyConfigurationError(ValueError):
    """The proxy settings cannot be read, so no client identity is trustworthy."""


def _trusts_proxy() -> bool:
    raw = os.environ.get("CEDAR_PRESS_TRUST_PROXY", "").strip()
    if raw in {"", "0"}:
        return False
    if raw == "1":
        return True
    raise ProxyConfigurationError("CEDAR_PRESS_TRUST_PROXY must be 0 or 1.")


def proxy_hops() -> int:
    """Trusted proxies in front of the API, or 0 when none is trusted."""
    if not _trusts_proxy():
        return 0
    raw = os.environ.get("CEDAR_PRESS_PROXY_HOPS", "").strip()
    if not raw:
        return DEFAULT_PROXY_HOPS
    if not raw.isdigit() or not 1 <= int(raw) <= _MAX_PROXY_HOPS:
        raise ProxyConfigurationError(
            f"CEDAR_PRESS_PROXY_HOPS must be a whole number from 1 to {_MAX_PROXY_HOPS}."
        )
    return int(raw)


def configuration_error(*, require_explicit: bool) -> str | None:
    """Why the proxy settings cannot be used, or ``None`` when they can.

    ``require_explicit`` is for staging and production, where an unset
    ``CEDAR_PRESS_TRUST_PROXY`` is refused rather than read as "no proxy":
    behind CloudFront that reading keys every subscriber to CloudFront's own
    address, and ten wrong passwords anywhere lock everyone out.
    """
    if require_explicit and not os.environ.get("CEDAR_PRESS_TRUST_PROXY", "").strip():
        return "CEDAR_PRESS_TRUST_PROXY must be set explicitly outside development."
    try:
        proxy_hops()
    except ProxyConfigurationError as error:
        return str(error)
    return None


def _address(raw: str | None) -> str | None:
    """A normalized address to limit by, or ``None`` if it is not one."""
    try:
        address = ipaddress.ip_address(str(raw or "").strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.IPv6Network(f"{address}/{_IPV6_PREFIX}", strict=False))
    return str(address)


def client_key(request) -> str:
    """Who is asking, for limiting purposes.

    ``X-Forwarded-For`` is a list each proxy appends to, so everything left of
    what our own proxies wrote is whatever the caller sent. The address we
    limit by is the one the outermost trusted proxy appended: the
    ``hops``-th entry counted from the right. Reading the left-most entry, as
    this once did, let a caller name a new identity on every request and
    never be limited at all.

    Every ``X-Forwarded-For`` header is read, in order, rather than the first:
    a caller can send their own header ahead of the one a proxy adds.

    A request carrying fewer entries than there are trusted proxies did not
    come through all of them, so nothing in its header is trusted and the
    socket peer is used instead.
    """
    hops = proxy_hops()
    client = getattr(request, "client", None)
    peer = _address(getattr(client, "host", None)) or getattr(client, "host", None) or "unknown"
    headers = getattr(request, "headers", None)
    values = headers.getlist("x-forwarded-for") if headers is not None else []
    if not hops:
        if values:
            _warn_untrusted_forwarding()
        return peer
    entries = [entry.strip() for value in values for entry in value.split(",")]
    if len(entries) < hops:
        return peer
    return _address(entries[-hops]) or peer


def _warn_untrusted_forwarding() -> None:
    """Say once that forwarded addresses are being ignored.

    Behind a proxy that is the global-lockout misconfiguration, and the
    service cannot tell it apart from a caller sending the header themselves,
    so it says so in the log rather than guessing.
    """
    global _warned_untrusted_forwarding
    if _warned_untrusted_forwarding:
        return
    _warned_untrusted_forwarding = True
    logger.warning(
        "X-Forwarded-For received but CEDAR_PRESS_TRUST_PROXY is not 1; rate limits are "
        "keyed by the socket peer. Behind a proxy, set CEDAR_PRESS_TRUST_PROXY=1 and "
        "CEDAR_PRESS_PROXY_HOPS."
    )


def reset_for_tests() -> None:
    with _lock:
        _hits.clear()
