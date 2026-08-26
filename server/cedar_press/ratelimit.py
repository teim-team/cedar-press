"""Rate limiting on the ways in.

WHY THIS EXISTS
An access code is 8 to 32 alphanumeric characters, and the activation routes
say plainly whether a given one is real. Without a limit that is an oracle:
an attacker with a script asks it a few million times and activates somebody
else's subscription. The same applies to sign-in, where the guessable secret
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

import os
import threading
from collections import defaultdict, deque
from time import monotonic

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


def client_key(request) -> str:
    """Who is asking, for limiting purposes.

    ``X-Forwarded-For`` is only read when the deployment says it sits behind a
    proxy. Trusting it unconditionally would hand every attacker a free reset:
    a header they control would become the identity they are limited by.
    """
    if os.environ.get("CEDAR_PRESS_TRUST_PROXY") == "1":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            # Left-most is the original client; the rest were added by hops.
            return forwarded.split(",")[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", None) or "unknown"


def reset_for_tests() -> None:
    with _lock:
        _hits.clear()
