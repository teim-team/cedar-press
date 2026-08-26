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
and the shelves and the downloads cannot disagree.

WHERE THE DATABASE GOES
Every route reads through ``repository.py``. Today that repository answers
from the ported modules; when the collections move into Postgres it answers
from there and nothing in this file changes. Routes hold HTTP concerns —
status codes, headers, the session — and no data access of their own, which
is what keeps that swap to one module.

RUNNING IT
    pip install -e server[dev]
    uvicorn cedar_press.app:app --reload --port 8000

Then point the client at it::

    VITE_API_URL=http://localhost:8000 npm run dev
"""

from __future__ import annotations

import io
import os

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from cedar_press import codes, repository
from cedar_press.session import (
    Session,
    account_exists,
    create_account,
    current_session,
    issue,
    sign_in,
    sign_out,
)

app = FastAPI(
    title="Cedar Press",
    description="The subscriber API behind cedarpress.ai.",
    version="0.1.0",
)

# The client is served from another origin (cedarpress.ai to the API's host),
# and the session rides in a cookie, so credentials must be allowed and the
# origin list must be explicit — "*" is not permitted with credentials, and
# should not be wanted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CEDAR_PRESS_ORIGINS", "http://localhost:5173,https://cedarpress.ai"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class Credentials(BaseModel):
    email: str
    password: str


class Question(BaseModel):
    question: str
    surface: str = "cedar-press"
    collectionId: str | None = None


def require_session(session: Session | None = Depends(current_session)) -> Session:
    """A route that reads subscriber data needs a subscriber.

    Entitlement is decided here rather than in the client: the client's
    ``pressAccess`` decides what renders, and this decides what is served.
    The two are written to answer identically, and this one is the control.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
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
def me(session: Session = Depends(require_session)) -> dict[str, object]:
    return session.as_payload()


@app.post("/auth/login")
def login(credentials: Credentials, response: Response) -> dict[str, object]:
    session = sign_in(credentials.email, credentials.password, response)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": (
                    "That sign-in did not work. Check the address and password on "
                    "your Cedar Press confirmation."
                ),
            },
        )
    return session.as_payload()


@app.post("/auth/logout", status_code=204)
def logout(response: Response) -> None:
    sign_out(response)


class CodeCheck(BaseModel):
    code: str
    email: str


class Activation(BaseModel):
    code: str
    email: str
    password: str


def _refuse(error_code: str) -> HTTPException:
    """A refusal the client already has copy for.

    The message is a fallback: ``pressSignupError`` renders its own wording
    per code, and this is what a caller that is not the client sees.
    """
    return HTTPException(
        status_code=400,
        detail={"code": error_code, "message": "That code could not be activated."},
    )


@app.post("/press/activation/validate", status_code=204)
def validate_code(check: CodeCheck) -> None:
    """Step one: is this code real, unspent, unexpired, and theirs?

    Creates nothing. The client asks this before showing the password field
    so a wrong code costs a message rather than a half-made account, and so
    the first screen a subscriber sees is two fields rather than four.
    """
    issued, error = codes.check(check.code, check.email)
    if error:
        raise _refuse(error)
    # Checked here as well as at activation: a reader who already has an
    # account should be sent to sign-in now, not after choosing a password.
    if account_exists(issued.email):
        raise _refuse(codes.EMAIL_IN_USE)


@app.post("/press/activation")
def activate(activation: Activation, response: Response) -> dict[str, object]:
    """Step two: create the account and sign them in.

    The code is re-checked rather than trusted from step one. Step one set no
    state, so nothing carries between the two calls, and an activation route
    that believed a client's word about a code it validated a moment ago
    would not need the code at all.

    The tier comes off the issued code, never off the request. Letting a
    caller name their own tier is how an activation route becomes an
    escalation route.
    """
    issued, error = codes.check(activation.code, activation.email)
    if error:
        raise _refuse(error)
    if account_exists(issued.email):
        raise _refuse(codes.EMAIL_IN_USE)
    if len(activation.password) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_TOO_SHORT",
                "message": "Choose a password of at least 10 characters.",
            },
        )

    session = create_account(issued.email, activation.password, issued.tier)
    # Spent only once the account exists. The other order loses a subscriber
    # their code if account creation fails.
    codes.spend(issued.code)
    return issue(session, response).as_payload()


@app.get("/press/collections")
def collections(session: Session = Depends(require_session)) -> dict[str, object]:
    """The catalog this subscription can see, with each entry's reach."""
    return {"collections": repository.collections_for(session.tier)}


@app.get("/press/releases")
def releases(session: Session = Depends(require_session)) -> dict[str, object]:
    return {"releases": repository.releases()}


@app.get("/press/articles")
def articles(session: Session = Depends(require_session)) -> dict[str, object]:
    return {"articles": repository.articles()}


@app.get("/press/collections/{collection_id}/download")
def download(
    collection_id: str, session: Session = Depends(require_session)
) -> StreamingResponse:
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
        raise HTTPException(status_code=404, detail="No such collection.")
    filename = repository.download_name(collection_id)
    return StreamingResponse(
        io.BytesIO(csv.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/cedar/ask")
def ask_cedar(
    question: Question, session: Session = Depends(require_session)
) -> dict[str, object]:
    """Cedar, scoped to what this subscription can open.

    Not implemented against the model yet, and it answers 501 rather than a
    plausible sentence: a stubbed assistant that invents an answer is worse
    than one that admits it is not wired, because only the second is
    obviously not the product.
    """
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Cedar is not yet answering from this service.",
        },
    )
