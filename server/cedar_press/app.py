"""Cedar Press: the API the reader talks to.

The React client in ``src/`` calls exactly these routes (see
``docs/ARCHITECTURE.md``), so this is the other half of that contract rather
than a second idea of what the service is.

WHY PYTHON
The collection, the citation register and the claim discipline were already
written in Python for Cedar Grove, and they are the part of this service with
real logic in it — inclusion rules, entity resolution, release bookkeeping,
CSV shaping. ``collections.py`` and ``press_catalog.py`` are those modules,
carried over rather than reimplemented, so a correction lands in one place
and the shelves and the downloads cannot disagree. Where the code came from,
not what it needs: this service imports nothing from Cedar Grove and calls no
Grove endpoint. Cedar Press runs standalone.

WHERE THE DATABASE GOES
Every route reads through ``repository.py``. Today that repository answers
from the ported modules; when the collections move into Postgres it answers
from there and nothing in this file changes. Routes hold HTTP concerns —
status codes, headers, the session — and no data access of their own, which
is what keeps that swap to one module.

A SECOND SURFACE, RENDERED HERE
``GET /press/shelf`` returns HTML rather than JSON: the shelf page, composed
by ``shelf.py`` from the same modules the JSON routes read and styled by the
client's own stylesheets. It is the working half of
the Python-first proposal of 2026-09-02 (``docs/PYTHON_FIRST_SITE.md``, at the
tag ``data-workspace-final``) — the demonstration that this service can
render the site, not only feed it. The React client is untouched and still
serves the same page; the two run side by side on purpose.

RUNNING IT
    pip install -e server[dev]
    uvicorn cedar_press.app:app --reload --port 8000

Then point the client at it::

    VITE_API_URL=http://localhost:8000 npm run dev

or open the server-rendered shelf directly::

    http://localhost:8000/press/shelf?tier=press_pro
"""

from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from cedar_press import (
    cedar_service,
    collection_profiles,
    need_profiles,
    press_catalog,
    priorities,
    protected_articles,
    release_research,
    repository,
    shelf,
)
from cedar_press.accounts.api.dependencies import auth_origins, require_account
from cedar_press.accounts.api.routes import router as accounts_router
from cedar_press.accounts.services import subscribers
from cedar_press.accounts.services.sessions import (
    Session,
    account_id_for,
    current_session,
)
from cedar_press.billing.api.routes import router as billing_router

app = FastAPI(
    title="Cedar Press",
    description="The subscriber API behind cedarpress.ai.",
    version="0.1.0",
)

# The client is served from another origin (cedarpress.ai to the API's host),
# and the session rides in a cookie, so credentials must be allowed and the
# origin list must be explicit — "*" is not permitted with credentials, and
# should not be wanted.
_AUTH_ORIGINS = auth_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_AUTH_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=[
        "Content-Disposition",
        "X-Cedar-Release",
        "X-Cedar-SHA256",
        "X-Cedar-Rows",
        "X-Cedar-Citation",
        "X-Cedar-Citation-Encoding",
    ],
)

# Responses compressed for any client that accepts gzip. The catalog alone,
# `/press/collections`, went out uncompressed (2026-10-04 audit); measured
# with the test accounts, 48,283 bytes become 11,469 for Cedar Press+ and
# 22,496 become 5,961 for Cedar Press, about 0.7 s saved at Slow 3G's
# 50 kB/s. Under ~1 kB the header costs more than compression saves.
# Level 6, not starlette's default 9: the streamed release downloads pass
# through here too, and 9 buys a few percent for several times the CPU. A
# browser decodes transparently, so `X-Cedar-SHA256` still describes the
# bytes a subscriber saves.
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

#: The repository root, from ``server/cedar_press/app.py``.
_REPO = Path(__file__).resolve().parents[2]

#: The client's own stylesheets and fonts, served to the server-rendered page.
#:
#: Mounted from the source tree rather than copied, which is the whole point:
#: the Python page must go stale the moment a designer edits press.css, not
#: keep serving a duplicate that agrees with nothing. A build would collect
#: these the way Vite already does for ``dist/``; the Python-first proposal
#: (``docs/PYTHON_FIRST_SITE.md``, at the tag ``data-workspace-final``) says
#: what that step becomes.
#:
#: Missing directories are skipped rather than raised on: the package is
#: installed with ``pip install -e server``, so a deployment that ships the
#: wheel without the repository around it still answers on every JSON route.
_STATIC = (("/styles", _REPO / "src" / "styles"), ("/fonts", _REPO / "public" / "fonts"))
for _path, _directory in _STATIC:
    if _directory.is_dir():
        app.mount(_path, StaticFiles(directory=_directory), name=_path.lstrip("/"))

_templates = Jinja2Templates(directory=Path(__file__).with_name("templates"))


class PointsMove(BaseModel):
    points: int


#: Upper bounds on what a subscriber types, enforced by the model so an
#: over-long body is a 422 before it reaches a store or Cedar. Generous beside
#: the forms (the Cedar panel's input stops at 280 characters; a research
#: request is a paragraph or two), and finite, so one request cannot write
#: megabytes into the requests table or forward them upstream.
MAX_REQUEST_TEXT = 4000
MAX_USE_CASE = 500
MAX_QUESTION = 1000


class ResearchRequest(BaseModel):
    text: str = Field(max_length=MAX_REQUEST_TEXT)
    use_case: str | None = Field(default=None, max_length=MAX_USE_CASE)
    priority_id: str | None = None
    support_points: int = 0


#: Shape the Research: one store for the process, seeded from the owner's
#: file on start. ``DATABASE_URL`` puts it in the platform's own database
#: beside teim-app's tables, and applies the migrations on the way; without
#: it the store falls back to SQLite at ``CEDAR_PRESS_DB``, or to memory,
#: which is right for a test and wrong for a deployment.
_priorities = priorities.open_store()


def _account(session: Session) -> priorities.Account:
    return priorities.Account(
        account_id=account_id_for(session.email),
        user_id=session.email,
        tier=session.tier,
    )


def _points_error(exc: priorities.PointsError) -> HTTPException:
    return HTTPException(status_code=400, detail={"code": "POINTS_REFUSED", "message": str(exc)})


class Question(BaseModel):
    question: str = Field(max_length=MAX_QUESTION)
    surface: str = "cedar-press"
    collectionId: str | None = None
    #: Cedar's own conversation id. Absent on the first turn -- Cedar mints
    #: one and returns it -- and echoed back on every turn after, which is
    #: what makes the panel a conversation rather than a sequence of
    #: unrelated questions.
    threadId: str | None = None
    #: Where in the product the question was asked. Passed through to Cedar
    #: as request context; it is the difference between answering a reader
    #: standing in front of a table and one reading a brief.
    pathname: str | None = None


def require_session(session: Session = Depends(require_account)) -> Session:
    """Paid or explicitly granted content access, independently of account sign-in."""
    if session.tier == "free":
        raise HTTPException(status_code=403, detail="A current subscription is required.")
    return session


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def _flatten_error(request: Request, exc: HTTPException):
    """Errors as `{code, message}`, which is the shape the client reads.

    FastAPI wraps `detail` in `{"detail": ...}`. The client reads
    `payload.code` and `payload.message` off the top level (see
    `src/api.js`), so every carefully worded refusal the routes raise was
    arriving as "Request failed (401)." — the wording was written, sent, and
    then thrown away one level down. Raising the flat shape in each route
    instead would work and would also mean every future route has to
    remember; doing it here means none of them do.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=getattr(exc, "headers", None),
        )
    return await http_exception_handler(request, exc)


@app.get("/me")
def me(session: Session = Depends(require_account)) -> dict[str, object]:
    # The first authenticated call of a visit: the month's points, once.
    if session.tier in subscribers.TIERS:
        _priorities.accrue(_account(session))
    return session.as_payload()


# ── Shape the Research ────────────────────────────────────────────────────


@app.get("/press/priorities")
def list_priorities(session: Session = Depends(require_session)) -> dict[str, object]:
    """Every priority with its points and subscriber count, most supported first."""
    return {
        "month": priorities.month_of(),
        "rules": {
            "points_per_active_month": priorities.POINTS_PER_ACTIVE_MONTH,
            "expiry_months": priorities.EXPIRY_MONTHS,
        },
        "priorities": _priorities.priorities(),
    }


@app.get("/press/priorities/related")
def related_priorities(
    q: str = "", session: Session = Depends(require_session)
) -> dict[str, object]:
    """The priorities a request reads as being about, before it is sent."""
    return {"matches": priorities.related(q, _priorities.priorities())}


@app.get("/press/influence")
def influence(session: Session = Depends(require_session)) -> dict[str, object]:
    """What this subscription has and has done: the profile's card.

    Credits the month first, once.
    """
    account = _account(session)
    _priorities.accrue(account)
    return _priorities.influence(account)


@app.post("/press/priorities/{priority_id}/points")
def move_points(
    priority_id: str,
    move: PointsMove,
    session: Session = Depends(require_session),
) -> dict[str, object]:
    """Put points on a priority (positive) or take them back (negative)."""
    account = _account(session)
    _priorities.accrue(account)
    try:
        return _priorities.allocate(account, priority_id, move.points)
    except priorities.PointsError as exc:
        raise _points_error(exc) from exc


@app.post("/press/requests", status_code=201)
def submit_request(
    body: ResearchRequest, session: Session = Depends(require_session)
) -> dict[str, object]:
    """A subscriber's own words, beside the priority they are about, with a point if asked."""
    account = _account(session)
    _priorities.accrue(account)
    try:
        return _priorities.submit_request(
            account, body.text, body.use_case, body.priority_id, body.support_points
        )
    except priorities.PointsError as exc:
        raise _points_error(exc) from exc


# ── The reader ────────────────────────────────────────────────────────────


class ReaderProfile(BaseModel):
    """What the reader says they work on; ``None`` withdraws the answer."""

    work: str | None = None


@app.get("/press/profile")
def read_profile(session: Session = Depends(require_account)) -> dict[str, object]:
    """The reader's declared work, per seat (``readerWork.js``)."""
    return _priorities.profile(session.email)


@app.patch("/press/profile")
def write_profile(
    body: ReaderProfile, session: Session = Depends(require_account)
) -> dict[str, object]:
    """Record what the reader declared. The vocabulary is the client's own
    (``WORK_KINDS``, dumped into ``_press_data.json``), so an answer the
    Settings page cannot offer is refused rather than stored."""
    if body.work is not None and body.work not in press_catalog.WORK_KINDS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNKNOWN_WORK",
                "message": "That is not one of the kinds of work the service asks about.",
            },
        )
    return _priorities.set_profile(session.email, body.work)


@app.get("/press/collections")
def collections(session: Session = Depends(require_session)) -> dict[str, object]:
    """The catalog this subscription can see, with each entry's reach."""
    return {"collections": repository.collections_for(session.tier)}


@app.get("/press/release-collections")
def release_collections(
    response: Response, session: Session = Depends(require_session)
) -> dict[str, object]:
    """Collection release integration targets with verified metadata when available."""
    try:
        subscriber = subscribers.find(session.email)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Authorization unavailable") from error
    if subscriber is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    response.headers["Cache-Control"] = "private, no-store"
    result = repository.release_targets_for(subscriber.tier)
    # A Grove subscriber can visit Press; its Press surface still has fourteen collections.
    result["collections"] = [entry for entry in result["collections"] if entry["id"] != "gaming"]
    return result


@app.get("/press/entities/{cedar_uid}/need-evidence")
def need_entity_evidence(
    cedar_uid: str,
    response: Response,
    session: Session = Depends(require_session),
) -> dict:
    """Sourced patent and rating observations for a registered entity,
    from the pinned NEED release.
    """
    if not repository.may_download_full(session.tier, "need"):
        raise HTTPException(status_code=403, detail="Collection not included")
    try:
        subscriber = subscribers.find(session.email)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Authorization unavailable") from error
    if subscriber is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not repository.may_download_full(subscriber.tier, "need"):
        raise HTTPException(status_code=403, detail="Collection not included")
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return need_profiles.entity_evidence(cedar_uid)
    except need_profiles.UnregisteredEntity as error:
        raise HTTPException(status_code=404, detail="No registered Native entity") from error
    except repository.FullReleaseUnavailable as error:
        raise HTTPException(status_code=503, detail="Verified NEED evidence unavailable") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid entity identifier") from error


@app.get("/press/shelf", response_class=HTMLResponse)
def press_shelf(
    request: Request,
    tier: str | None = None,
    session: Session | None = Depends(current_session),
) -> HTMLResponse:
    """The shelf page, rendered as HTML by this service.

    The one route here that returns a page rather than a payload, and the
    working half of the Python-first proposal (``docs/PYTHON_FIRST_SITE.md``,
    at the tag ``data-workspace-final``): the same collection
    descriptors, access rule, catalog copy and release history the JSON routes
    serve, composed by ``shelf.py`` and laid out by the client's own
    ``press.css``. Nothing on it is read from a JavaScript module.

    NO SESSION IS REQUIRED, AND NOTHING IS GIVEN AWAY
    A signed-in reader's plan wins. Without a session the ``tier`` query
    decides, defaulting to the cheapest plan, so a reviewer with a link can
    see what each plan is shown without an account being made for them.

    That is safe because this page renders descriptions and not records: the
    names, blurbs and coverage years the public gate already carries. Every
    download on it submits to ``/press/collections/{id}/download``, which
    still requires a session and still asks ``repository.may_open``. The
    query changes what is described. It cannot change what is served.
    """
    view = shelf.view_for(session.tier if session else shelf.resolve_tier(tier))
    return _templates.TemplateResponse(
        request,
        "shelf.html",
        {"view": view, "tiers": shelf.KNOWN_TIERS},
        # Not indexed, and not cached by anything shared: the page differs per
        # plan, and a proxy that kept one reader's shelf would hand it to the
        # next.
        headers={"X-Robots-Tag": "noindex", "Cache-Control": "private, no-store"},
    )


@app.get("/press/releases")
def releases(response: Response, session: Session = Depends(require_session)) -> dict[str, object]:
    response.headers["Cache-Control"] = "private, no-store"
    try:
        subscriber = subscribers.find(session.email)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Authorization unavailable") from error
    if subscriber is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return repository.releases(subscriber.tier)


def require_article_reader(session: Session | None = Depends(current_session)) -> Session:
    if session is None:
        raise HTTPException(
            status_code=401, detail="Not signed in.", headers=protected_articles.ARTICLE_HEADERS
        )
    if not press_catalog.can_read_cedar_press(session.tier):
        raise HTTPException(
            status_code=403,
            detail="This subscription does not include Cedar Press articles.",
            headers=protected_articles.ARTICLE_HEADERS,
        )
    return session


@app.get("/press/articles")
def articles(session: Session = Depends(require_article_reader)) -> JSONResponse:
    return JSONResponse(
        {"articles": protected_articles.article_cards()},
        headers=protected_articles.ARTICLE_HEADERS,
    )


@app.get("/press/articles/{slug}")
def article(slug: str, session: Session = Depends(require_article_reader)) -> JSONResponse:
    found = protected_articles.article_detail(slug)
    if found is None:
        raise HTTPException(
            status_code=404, detail="No such article.", headers=protected_articles.ARTICLE_HEADERS
        )
    return JSONResponse({"article": found}, headers=protected_articles.ARTICLE_HEADERS)


DOWNLOAD_LOG = logging.getLogger("cedar_press.download")
DOWNLOAD_LOG.setLevel(logging.INFO)
if not DOWNLOAD_LOG.handlers:
    DOWNLOAD_LOG.addHandler(logging.StreamHandler())


def _download_audit(
    collection_id, outcome, release=None, requested_release_id=None, component=None
):
    component_release = repository.is_component_release(collection_id)
    safe_collection = (
        collection_id
        if component_release
        or any(item.id == collection_id for item in repository.launch.LAUNCH_COLLECTION)
        else "unknown"
    )
    event = {
        "event": "full_download",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "requested_release_id": requested_release_id
        if isinstance(requested_release_id, str)
        and re.fullmatch(r"[0-9a-f]{64}", requested_release_id)
        else None,
        "request_id": uuid.uuid4().hex,
        "collection_id": safe_collection,
        "outcome": outcome,
        "release_id": release.get("release_id") if release else None,
        "sha256": release.get("sha256") if release else None,
    }
    if component_release:
        # A collection release has governed components: the record names
        # which one, redacted like the collection when it is not a declared one.
        event["component"] = (
            component
            if component in repository.grove_components(collection_id)
            else ("unknown" if component is not None else None)
        )
    DOWNLOAD_LOG.info(json.dumps(event, sort_keys=True))


@app.get("/press/collections/{collection_id}/research")
def release_research_preview(
    collection_id: str,
    release_id: str,
    component: str | None = None,
    session: Session | None = Depends(current_session),
):
    """Real bounded examples and definitions behind the same live-account gates as downloads."""
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not repository.may_download_full(session.tier, collection_id):
        raise HTTPException(status_code=403, detail="Collection not included")
    try:
        subscriber = subscribers.find(session.email)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Authorization unavailable") from error
    if subscriber is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not repository.may_download_full(subscriber.tier, collection_id):
        raise HTTPException(status_code=403, detail="Collection not included")
    try:
        payload = release_research.packet(subscriber.tier, collection_id, release_id, component)
    except (repository.FullReleaseUnavailable, OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=503, detail="The research preview is currently unavailable or unverifiable."
        ) from error
    return JSONResponse(
        payload, headers={"Cache-Control": "private, no-store", "X-Cedar-Release": release_id}
    )


class _VerifiedDownloadResponse(StreamingResponse):
    """Own the private spool even when sending headers fails or is cancelled."""

    def __init__(self, spool, **kwargs):
        self.spool = spool
        super().__init__(self.chunks(), **kwargs)

    def chunks(self):
        while chunk := self.spool.read(64 * 1024):
            yield chunk

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.spool.close()


@app.get("/press/collections/{collection_id}/spreadsheet-download")
@app.get("/press/collections/{collection_id}/full-download")
def full_download(
    collection_id: str,
    request: Request,
    release_id: str | None = None,
    component: str | None = None,
    session: Session | None = Depends(current_session),
):
    """One pinned full release: a Press flagship, or one governed component of a
    collection the reviewed Grove declaration names (``component`` required).
    Entitlement is decided before any catalog or artifact is read."""

    def audit(outcome, release=None, requested=release_id):
        _download_audit(collection_id, outcome, release, requested, component)

    if session is None:
        audit("denied_anonymous")
        raise HTTPException(status_code=401, detail="Authentication required")
    if not repository.may_download_full(session.tier, collection_id):
        audit("denied_entitlement")
        raise HTTPException(status_code=403, detail="Collection not included")
    # A signed cookie proves a prior login, not a current subscription. Use the
    # existing account authority before touching a protected release; an account
    # outage must not fall back to the cookie's stale tier.
    try:
        subscriber = subscribers.find(session.email)
    except Exception as error:
        audit("authorization_unavailable")
        raise HTTPException(status_code=503, detail="Authorization unavailable") from error
    if subscriber is None:
        audit("denied_account")
        raise HTTPException(status_code=401, detail="Authentication required")
    if not repository.may_download_full(subscriber.tier, collection_id):
        audit("denied_entitlement")
        raise HTTPException(status_code=403, detail="Collection not included")
    try:
        if not release_id or not re.fullmatch(r"[0-9a-f]{64}", release_id):
            audit("invalid_release_request", requested=None)
            raise HTTPException(status_code=400, detail="Explicit release ID required")
        if request.url.path.endswith("/spreadsheet-download"):
            from cedar_press.spreadsheet import download as spreadsheet_download

            if component is not None:
                raise HTTPException(status_code=400, detail="Choose the collection spreadsheet")
            release = spreadsheet_download(collection_id, release_id)
        else:
            # Retain the exact legacy participant download when a native release is
            # still pinned. New collection releases require an explicit component;
            # no ambiguous combined table or silent release substitution is offered.
            legacy_federal = collection_id == "federal-register" and component is None
            if (
                repository.is_component_release(collection_id)
                and component is None
                and not legacy_federal
            ):
                audit("invalid_release_request")
                raise HTTPException(status_code=400, detail="Explicit component required")
            if repository.is_component_release(collection_id) and not legacy_federal:
                release = repository.grove_full_release(
                    collection_id, release_id, component=component
                )
            elif component is not None:
                audit("invalid_release_request")
                raise HTTPException(status_code=400, detail="A Press flagship has no components")
            else:
                release = repository.full_release(collection_id, release_id)
    except repository.GroveReleaseNotPinned as error:
        # Production state until the Gaming IDs are issued: say so plainly,
        # never substitute a sample or an unpinned file.
        audit("not_pinned")
        raise HTTPException(
            status_code=503, detail="No released data is pinned for this collection yet"
        ) from error
    except repository.FullReleaseUnavailable as error:
        audit("unavailable")
        raise HTTPException(status_code=503, detail="Full release unavailable") from error
    audit("authorized_prepared", release)
    headers = {
        "Content-Disposition": f'attachment; filename="{release["filename"]}"',
        "X-Cedar-Release": release["release_id"],
        "X-Cedar-SHA256": release["sha256"],
        "X-Cedar-Rows": str(release["record_count"]),
        "X-Cedar-Citation": quote(release["citation"], safe=' ,.:/()"-'),
        "X-Cedar-Citation-Encoding": "percent",
        "Cache-Control": "private, no-store",
    }
    if release.get("component"):
        headers["X-Cedar-Component"] = release["component"]
    # A Grove component arrives as a verified `content_file`; a partitioned Press
    # flagship as a verified `spool`. Both are disk spools the response closes.
    spool = release.get("content_file") or release.get("spool")
    if spool is not None:
        return _VerifiedDownloadResponse(
            spool,
            media_type=release["media_type"],
            headers=headers,
        )
    return Response(content=release["content"], media_type=release["media_type"], headers=headers)


@app.get("/press/collections/{collection_id}/download")
def download(collection_id: str, session: Session = Depends(require_session)) -> StreamingResponse:
    """A release file.

    The entitlement check is here and not only on the shelf: a reader who
    guesses a collection id must not be handed a file their subscription does
    not include, and the shelf hiding a tile is a display decision.
    """
    if not repository.may_open(session.tier, collection_id):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "NOT_INCLUDED",
                "message": "That collection is not included in this subscription.",
            },
        )
    csv = repository.collection_csv(collection_id)
    if csv is None:
        # A collection on the shelf whose preview Cedar cannot produce is a
        # named data problem, not a missing route, and the reader is told
        # which. Answering both with "No such collection" is how a real
        # unresolved question disappears into a routing message.
        reason = repository.sample_unavailable_reason(collection_id)
        if reason:
            raise HTTPException(
                status_code=409,
                detail={"code": "NO_SAMPLE", "message": reason},
            )
        raise HTTPException(status_code=404, detail="No such collection.")
    filename = repository.download_name(collection_id)
    return StreamingResponse(
        io.BytesIO(csv.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/press/collections/{collection_id}/profile")
def collection_profile(
    collection_id: str, session: Session = Depends(require_session)
) -> dict[str, object]:
    """The collection's machine-readable profile: the living data dictionary.

    Served to any signed-in reader regardless of shelf: the profile is the
    description of a collection, not its records, and describing what a
    higher shelf holds is the honest version of an upgrade prompt.
    """
    profile = repository.collection_profile(collection_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No such collection.")
    return profile


def _answer_basis(
    kind: str,
    profile: dict[str, object] | None,
    collection_id: str | None,
    *,
    opened: bool = True,
) -> dict[str, object]:
    """The answer's basis, structured, for the label the panel shows above it.

    THE POINT OF THIS BEING AN OBJECT AND NOT A SENTENCE.
    A reader cannot tell a reading of a release from a composed reply by
    looking at the prose — that is the whole difficulty, and it is why the
    basis has to be stated rather than inferred. A string could be shown, but
    only an object can be *checked*: the panel renders the release, the date
    and the source families because they are fields, and renders nothing
    where there is no field rather than a plausible blank.

    ``kind`` is one of:

    ``release``     read off the collection's own release, cited to it
    ``synthesis``   Cedar composed it; scope is real, the records are not cited
    ``review``      the identity, evidence or scope is ambiguous

    ``review`` HAS NO PRODUCER TODAY and is here as a declared state rather
    than a promise. Nothing in this service can currently detect an ambiguous
    identity — the profiles either answer or return ``None``, and the Cedar
    service returns prose. It will have one when Cedar can retrieve from the
    register, and the shape is here so that arriving is a change of one value
    rather than a change of the contract.

    ``cited_records`` is deliberately absent rather than ``0``. Cedar returns
    no record citations at all, and a zero would be read as "checked, found
    none" by every reader and every downstream renderer.

    ``opened`` IS A SECOND AXIS AND NOT A FOURTH KIND.
    ``kind`` says what produced the answer; ``opened`` says whether this
    subscription reaches the records behind it. They are independent, and the
    combination that proves it is the locked collection: its description is
    read off the release and cited to it -- a true ``release`` -- while its
    records stay shut. Folding that into ``kind`` as a "description" state
    would lose the citation, and leaving it out entirely is what the panel
    was doing: it rendered "View supporting records" under an answer whose
    last sentence had just said those records open with another plan.
    """
    profile = profile or {}
    version = profile.get("version")
    name = profile.get("collection_name")
    basis: dict[str, object] = {
        "kind": kind,
        "collectionId": collection_id,
        "collectionName": name,
        "version": version,
        "updated": profile.get("last_updated"),
        "opened": opened,
    }
    if kind == "release":
        # Only a release-grounded answer may name the sources it came from:
        # these are the profile's own, and the answer was read off that
        # profile. A synthesis did not read them, so it does not cite them.
        basis["sources"] = profile.get("primary_sources")
    return basis


def _not_included_answer(
    profile: dict[str, object], collection_id: str, thread_id: str | None
) -> dict[str, object]:
    """The honest reply for a collection this subscription does not include.

    Not a refusal, and not a sales page. The description of a collection is
    not its records, and this service already decided that distinction the
    other way round on ``/press/collections/{id}/profile``, which serves any
    signed-in reader "because describing what a higher shelf holds is the
    honest version of an upgrade prompt". A reader who asks about Cedar NEED
    on a Press subscription gets what NEED is, read off its release, and is
    told plainly where the records live.

    What they do not get is retrieval. This return still does not hop.
    A profile miss on the same locked page does hop, with the page id as
    context, and the records stay closed because that id is not in
    ``allowedCollectionIds``. ``access.opened`` is a field rather than a
    tone so a panel can render the boundary instead of inferring it from
    the prose.
    """
    description = profile.get("description")
    name = profile.get("collection_name") or collection_id
    reach = (
        f"{name} is part of Cedar Press+. This is what the collection is, "
        f"read off its current release; its records open with that plan."
    )
    return {
        "answer": f"{description}\n\n{reach}" if description else reach,
        "basis": None,
        "answerBasis": _answer_basis("release", profile, collection_id, opened=False),
        "collectionId": collection_id,
        # The description came off the release, so the basis is a release and
        # says so. `source` names the answerer, and no answerer ran past the
        # profile: Cedar was never asked.
        "source": "profile",
        "access": {
            "opened": False,
            "plan": "Cedar Press+",
            "reason": "NOT_INCLUDED",
        },
        "threadId": thread_id,
    }


def _ask_which_collection(thread_id: str | None) -> dict[str, object]:
    """One question back, for a question with no collection under it.

    THE CASE THIS IS, AND THE CASE IT IS NOT.
    Two very different situations used to end at the same ``NOT_ANSWERABLE``
    paragraph. A reader who named a collection and asked something its
    release does not state has been refused, correctly: they supplied the
    context and the answer is genuinely not here. A reader who asked without
    naming one has not been refused -- they have been *understood
    incompletely*, and the single missing thing is the collection. Answering
    both with "open a collection and ask from there. Anything past that needs
    Cedar itself, which is not wired into this deployment; the research desk
    ... answers those in person" is three instructions and an apology where
    one question would do, and it reads as a system explaining its own
    routing rather than as somebody trying to help.

    So this asks the one thing that would let the next turn answer, and says
    what naming it buys -- which is not a promise: ``answer_from_profile``
    really does answer those three from the collection's own release. It is
    not a list of filters and it does not ask anybody to phrase a query.

    NO ``answerBasis``. The label above a bubble says what a claim rests on,
    and this bubble makes no claim. A basis here would have to invent a kind
    for "this is a question", and a reader would be shown a citation line
    under a sentence citing nothing.
    """
    return {
        "answer": (
            "Which collection are you asking about? Name one and I can tell "
            "you what it holds, where its records come from, and what its "
            "latest release reports."
        ),
        "basis": None,
        "answerBasis": None,
        "collectionId": None,
        # `source` names the answerer, and nothing answered: the route asked.
        "source": None,
        "threadId": thread_id,
    }


def _cedar_counts_these_records(question: Question, tier: str) -> bool:
    """Whether Cedar, not the profile, should answer this figures question.

    The profile states release-level figures. A count or total for one
    entity or one year is read from the records, and Cedar can read them when
    it is wired and this plan's allow-list carries the page's collection.
    """
    collection_id = question.collectionId
    if not collection_id or not cedar_service.available():
        return False
    if not collection_profiles.asks_for_figures(question.question):
        return False
    if not collection_profiles.asks_about_specific_records(question.question, collection_id):
        return False
    allowed, _pins = cedar_service.retrieval_allowlist(tier)
    return collection_id in allowed


@app.post("/cedar/ask")
def ask_cedar(question: Question, session: Session = Depends(require_session)) -> dict[str, object]:
    """Cedar, scoped to what this subscription can open.

    The profile answerer sees the page id before the locked-hit decision.
    Cedar sees a hop only after that. The hop's retrieval set is the payload
    allow-list, not this page.

    ``repository.may_open`` is the same rule the shelf and the download route
    read. ``_payload`` walks the storefront with that rule and sends
    ``allowedCollectionIds`` plus ``pinnedReleaseIds``. The page id stays on
    ``collectionId`` and does not remove ids from that list. A profile answer
    for a sold collection this plan cannot open returns ``_not_included_answer``
    and does not hop. Any other question hops. Two questions skip the profile:
    one that names another collection (the profile answers only for its own
    page), and a figures question about one entity or one year on a collection
    Cedar can read (``_cedar_counts_these_records``). A hidden control in the browser,
    an omitted sample request and a client-supplied plan are all display
    decisions, and none of them is authorization.

    TWO ANSWERERS, IN THIS ORDER, AND THE ORDER IS THE POINT.

    1. **The collection's own profile.** Scoped to a collection, what it
       contains, how it was constructed and its headline figures are read
       straight off ``collection_profiles.py`` and returned with a ``basis``
       naming the release they came from. No model is consulted, because no
       model is needed to read a fact the release already states, and an
       answer that cites its release is a better answer than one that
       paraphrases it.
    2. **Cedar.** Everything the profiles cannot answer goes to the service
       in the ``cedar`` repository over contract 1.0.0 -- the same Cedar
       ``teim-app`` talks to, not a second assistant wearing the name. See
       ``cedar_service.py`` for why the hop happens here and not in the
       browser.

    Past both, it either asks for the one thing that would let it answer or
    refuses and names the research desk -- ``_ask_which_collection`` says
    which case is which. Refusing remains the floor: an assistant that
    produces a plausible sentence it cannot support is worse than one that
    hands the question to a person.
    """
    profile = None
    collection_name = None
    if question.collectionId:
        profile = repository.collection_profile(question.collectionId)
        if profile is None:
            raise HTTPException(status_code=404, detail="No such collection.")
        collection_name = profile.get("collection_name")
        answered = repository.cedar_answer(question.question, question.collectionId)
        if answered and _cedar_counts_these_records(question, session.tier):
            answered = None
        if (
            answered
            and repository.is_sold(question.collectionId)
            and not repository.may_open(session.tier, question.collectionId)
        ):
            return _not_included_answer(
                profile, question.collectionId, question.threadId
            )
        if answered:
            return {
                "answer": answered["answer"],
                "basis": answered["basis"],
                "answerBasis": _answer_basis("release", profile, question.collectionId),
                "collectionId": question.collectionId,
                "source": "profile",
                "threadId": question.threadId,
            }

    if cedar_service.available():
        try:
            reply = cedar_service.ask(
                question=question.question,
                email=session.email,
                tier=session.tier,
                thread_id=question.threadId,
                collection_id=question.collectionId,
                collection_name=collection_name,
                pathname=question.pathname,
            )
            if reply.unavailable:
                raise cedar_service.CedarUnavailable("Cedar reported that it is unavailable.")
        except cedar_service.CedarUnavailable:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "CEDAR_UNAVAILABLE",
                    "message": (
                        "Cedar could not be reached just now. The collection "
                        "profiles still answer what a collection holds, how it "
                        "was built and its published figures."
                    ),
                },
            ) from None
        return {
            "answer": reply.answer,
            # Only the profile path can cite a release. Cedar's own answers
            # carry no basis sentence rather than a fabricated one — but they
            # do carry a scope, which is a real fact about the question and
            # is what `synthesis` states.
            "basis": None,
            "answerBasis": _answer_basis(
                "synthesis",
                profile,
                question.collectionId,
                opened=repository.may_open(session.tier, question.collectionId)
                if question.collectionId
                else True,
            ),
            "collectionId": question.collectionId,
            "source": "cedar",
            "threadId": reply.thread_id or question.threadId,
            "unavailable": reply.unavailable,
        }

    # Nobody named a collection, so the missing piece is one this reader can
    # supply and the next turn can use. See `_ask_which_collection`.
    if not question.collectionId:
        return _ask_which_collection(question.threadId)

    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_ANSWERABLE",
            "message": (
                "That is past what the current release of "
                f"{collection_name or 'this collection'} states, and Cedar "
                "itself is not wired into this deployment. The research desk "
                "(contact@lumecon.ai) answers questions like it in person."
            ),
        },
    )


app.include_router(billing_router)

app.include_router(accounts_router)
