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

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cedar_press import repository
from cedar_press.session import Session, current_session, sign_in, sign_out

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
                "message": "That sign-in did not work. Check the address and password on your Cedar Press confirmation.",
            },
        )
    return session.as_payload()


@app.post("/auth/logout", status_code=204)
def logout(response: Response) -> None:
    sign_out(response)


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
