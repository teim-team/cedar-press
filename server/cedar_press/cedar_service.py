"""The client for Cedar — the real one, in the ``cedar`` repository.

WHY THIS FILE EXISTS
Cedar Press shipped its own idea of an assistant: a textarea that POSTed to
``/cedar/ask`` and got one paragraph back. Meanwhile the assistant this
company actually built answers at ``POST /api/v1/messages`` in the ``cedar``
service, and ``teim-app`` has been talking to it since contract ``1.0.0``.
Two products, two different assistants, one name. This is Cedar Press joining
the contract rather than keeping a second one.

THE CONTRACT, AND WHERE IT IS WRITTEN DOWN
``teim-app/server/cedar/client.js`` builds the request and
``cedar/schemas/chat.py`` receives it. Both were read to write this, and the
field names below are theirs, not a guess:

    POST {CEDAR_BASE_URL}/api/v1/messages
    Authorization: Bearer {CEDAR_INTERNAL_API_KEY}
    {version, requestId, threadId, user, project, projectContext,
     context, message}
 -> {messageId, threadId, answer, contextUsed, unavailable}

``threadId`` is what makes it a conversation: Cedar generates one on the first
turn and the client sends it back on every turn after. The panel keeps it for
the life of the panel.

WHY THE SERVER CALLS IT AND NOT THE BROWSER
The key is an internal one (``require_internal_key``, a bearer token shared
between services). A browser cannot hold it, so the reader's request arrives
here on a session cookie, is checked against the subscription, and is then
re-issued to Cedar over the internal contract. Entitlement is decided on this
side of that hop, which is the arrangement ``teim-app`` already uses.

THE SAME ENVIRONMENT SURFACE AS teim-app
Deliberately not a new set of names. ``CEDAR_BASE_URL``,
``CEDAR_INTERNAL_API_KEY`` (falling back to ``CEDAR_API_KEY``),
``CEDAR_API_PATH``, ``CEDAR_TIMEOUT_MS`` and ``CEDAR_ENABLED`` are read here
exactly as ``teim-app/server/cedar/client.js`` reads them, down to
``CEDAR_ENABLED`` treating only the literal ``"false"`` as off. Two products
talking to one service should be configurable from one set of variables, and
a second spelling of a knob is how a deployment comes to set the wrong one.

WHEN IT IS NOT CONFIGURED
``CEDAR_BASE_URL`` unset, no key, or ``CEDAR_ENABLED=false`` means Cedar is
not wired into this deployment, and ``available()`` is False. The route then answers from the collection profiles
alone and, past those, refuses and names the research desk. It does not
apologise on Cedar's behalf for a service it was never pointed at.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: The contract this client speaks. Matches ``CEDAR_CONTRACT_VERSION`` in
#: ``teim-app/server/cedar/client.js``; bump both together or not at all.
CONTRACT_VERSION = "1.0.0"

#: Where the messages endpoint lives, under whatever base URL is configured.
#: ``api/v1/router.py`` mounts ``/v1`` and ``/messages`` under it, and the app
#: mounts that under ``/api`` — so the default is the same one ``teim-app``
#: names in ``DEFAULT_CHAT_PATH``, and ``CEDAR_API_PATH`` overrides it there
#: and here alike.
DEFAULT_CHAT_PATH = "/api/v1/messages"

#: Cedar reasons about a question before it answers, so this is a patience
#: limit rather than a liveness one. ``teim-app``'s default is 120s; a reader
#: watching a panel will not wait that long, so Press's default is shorter and
#: the panel says so. Same variable and same units as teim-app, because two
#: names for one knob is how a deployment ends up setting the wrong one.
DEFAULT_TIMEOUT_MS = 45_000


def _truthy_enabled(value: str | None) -> bool:
    """``CEDAR_ENABLED``, read exactly as ``teim-app`` reads it.

    Its ``parseEnabled`` treats *unset* as enabled and only the literal
    string ``"false"`` as off. Copied rather than improved: a deployment that
    sets one variable for both services must get the same answer from both,
    and "Press interpreted the kill switch differently" is not a failure
    anyone would look for.
    """
    return value is None or value != "false"


def chat_path() -> str:
    path = os.environ.get("CEDAR_API_PATH", "").strip() or DEFAULT_CHAT_PATH
    return path if path.startswith("/") else f"/{path}"


def timeout_seconds() -> float:
    try:
        milliseconds = float(os.environ.get("CEDAR_TIMEOUT_MS", DEFAULT_TIMEOUT_MS))
    except ValueError:
        milliseconds = DEFAULT_TIMEOUT_MS
    if not (milliseconds > 0):
        milliseconds = DEFAULT_TIMEOUT_MS
    return milliseconds / 1000.0


def api_key() -> str:
    """``CEDAR_INTERNAL_API_KEY``, then ``CEDAR_API_KEY``, as teim-app does."""
    return (
        os.environ.get("CEDAR_INTERNAL_API_KEY", "").strip()
        or os.environ.get("CEDAR_API_KEY", "").strip()
    )


class CedarUnavailable(Exception):
    """Cedar could not be reached, or answered in a shape this cannot read.

    Distinct from "Cedar declined to answer": the caller tells the reader
    different things, and conflating the two is how a service outage comes to
    look like a limit of the product.
    """


@dataclass(frozen=True)
class CedarReply:
    answer: str
    thread_id: str | None
    unavailable: bool


def base_url() -> str:
    return os.environ.get("CEDAR_BASE_URL", "").strip().rstrip("/")


def available() -> bool:
    """Whether this deployment has been pointed at Cedar at all.

    Three conditions, in teim-app's own terms: the kill switch is not off, a
    base URL is set, and there is a key. A base URL with no key gets a 401
    from every call, which is a misconfiguration worth reporting as "not
    wired" rather than as an outage.
    """
    return (
        _truthy_enabled(os.environ.get("CEDAR_ENABLED"))
        and bool(base_url())
        and bool(api_key())
    )


def _payload(
    *,
    question: str,
    email: str,
    tier: str,
    thread_id: str | None,
    collection_id: str | None,
    collection_name: str | None,
    pathname: str | None,
) -> dict[str, object]:
    """The request body, in the contract's own field names.

    ``project`` is required by the schema and is a TEIM concept — a modelled
    project with an analysis year. Cedar Press has no such thing, so the
    collection under the reader's question takes that slot, named so the
    service's logs and ``contextUsed`` read truthfully rather than carrying a
    placeholder that looks like a project id.
    """
    request_id = f"press-{uuid.uuid4()}"
    project_id = f"collection:{collection_id}" if collection_id else "cedar-press"
    project_name = collection_name or "Cedar Press"
    return {
        "version": CONTRACT_VERSION,
        "requestId": request_id,
        "threadId": thread_id,
        "user": {"id": email, "email": email},
        "project": {
            "id": project_id,
            "name": project_name,
            "analysisYear": None,
            # Everything Cedar needs to know that this is a Press reader and
            # what they may open. The service decides nothing about
            # entitlement; it is told, because entitlement was already
            # decided on this side of the hop.
            "projectData": {
                "surface": "cedar-press",
                "tier": tier,
                "collectionId": collection_id,
                "collectionName": collection_name,
            },
        },
        "context": {
            "route": "cedar-press",
            "pathname": pathname,
        },
        "message": {"id": request_id, "text": question},
    }


def ask(
    *,
    question: str,
    email: str,
    tier: str,
    thread_id: str | None = None,
    collection_id: str | None = None,
    collection_name: str | None = None,
    pathname: str | None = None,
) -> CedarReply:
    """One turn of a conversation with Cedar.

    Raises :class:`CedarUnavailable` for anything that is not an answer —
    unconfigured, unreachable, a non-2xx status, or a body without an
    ``answer`` in it. The caller decides what a reader is told.
    """
    if not available():
        raise CedarUnavailable("Cedar is not configured for this deployment.")

    body = json.dumps(
        _payload(
            question=question,
            email=email,
            tier=tier,
            thread_id=thread_id,
            collection_id=collection_id,
            collection_name=collection_name,
            pathname=pathname,
        )
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url()}{chat_path()}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # a status, which is worth logging
        detail = exc.read().decode("utf-8", "replace")[:400]
        logger.warning("Cedar returned %s: %s", exc.code, detail)
        raise CedarUnavailable(f"Cedar returned {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Cedar could not be reached: %s", exc)
        raise CedarUnavailable("Cedar could not be reached.") from exc

    answer = (payload or {}).get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise CedarUnavailable("Cedar returned no answer.")
    return CedarReply(
        answer=answer.strip(),
        thread_id=(payload.get("threadId") or None),
        # The contract carries its own degraded flag. Cedar saying "I am
        # unavailable" in a 200 is not the same as an answer, and the panel
        # must not file it under one.
        unavailable=bool(payload.get("unavailable")),
    )
