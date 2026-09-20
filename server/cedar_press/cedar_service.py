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

WHEN IT IS NOT CONFIGURED
``CEDAR_BASE_URL`` unset means Cedar is not wired into this deployment, and
``available()`` is False. The route then answers from the collection profiles
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
#: mounts that under ``/api`` — so the path is the same one ``teim-app`` names
#: in ``DEFAULT_CHAT_PATH``.
CHAT_PATH = "/api/v1/messages"

#: Cedar reasons about a question before it answers, so this is a patience
#: limit rather than a liveness one. ``teim-app`` allows 120s; a reader
#: watching a panel will not, so this is shorter and the panel says so.
TIMEOUT_SECONDS = float(os.environ.get("CEDAR_TIMEOUT_SECONDS", "45"))


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

    Both halves are required: a base URL with no key gets a 401 from every
    call, which is a misconfiguration worth reporting as "not wired" rather
    than as an outage.
    """
    return bool(base_url()) and bool(os.environ.get("CEDAR_INTERNAL_API_KEY", "").strip())


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
        f"{base_url()}{CHAT_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['CEDAR_INTERNAL_API_KEY'].strip()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
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
