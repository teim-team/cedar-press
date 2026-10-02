"""Subscriber article content, stored outside the public web build."""

from __future__ import annotations

import ipaddress
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

_CONTENT = Path(__file__).with_name("articles.json")
CARD_FIELDS = (
    "id",
    "hosted",
    "demonstration",
    "earlyAccess",
    "draft",
    "tone",
    "image",
    "imageAlt",
    "caption",
    "credit",
    "datasetId",
    "draws",
    "tag",
    "title",
    "dek",
    "date",
    "byline",
    "minutes",
    "kind",
    "href",
)
_TEXT_BLOCKS = frozenset({"p", "h2", "pull"})
_IMAGE_FIELDS = ("src", "alt", "caption", "credit", "tone")
ARTICLE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Cookie",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
}


def _public_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (
            parsed.scheme not in {"http", "https"}
            or not host
            or parsed.username
            or parsed.password
            or "." not in host
            or host.lower().endswith((".local", ".internal", ".localhost"))
        ):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        return value
    except ValueError:
        return None


def _image_url(value):
    if (
        isinstance(value, str)
        and value.startswith(("/pitch/", "/photo/"))
        and not any(token in value for token in ("..", "\\", "%", "?", "#"))
    ):
        return value
    return _public_url(value)


def _fields(record, names):
    return {key: record[key] for key in names if key in record}


def _image(record):
    result = _fields(record, _IMAGE_FIELDS)
    result["src"] = _image_url(record.get("src"))
    return result


def _sources(records):
    output = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        url = _public_url(record.get("url"))
        if url:
            output.append(
                {
                    **_fields(record, ("title", "publisher", "date", "accessed", "locator")),
                    "url": url,
                }
            )
    return output


def _text_block(record):
    """Turn Markdown links into cited text without interpreting HTML."""
    result = _fields(record, ("kind", "text"))
    citations = _sources(record.get("sources", []))

    def cite(match):
        label, candidate = match.groups()
        if (url := _public_url(candidate)) and not any(item["url"] == url for item in citations):
            citations.append({"title": label, "url": url})
        return label

    result["text"] = re.sub(
        r"\[([^\]\n]{1,200})\]\(([^()\s]+)\)", cite, str(record.get("text", ""))
    )
    if citations:
        result["citations"] = citations
    return result


_EVIDENCE_CHARTS = frozenset({"relationships", "timeline", "evidenceTable"})
_EVIDENCE_COLUMNS = frozenset({"entity", "role", "asOf", "detail"})


def _evidence_text(record, key, *, limit=4000):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Invalid evidence {key}")
    return value


def _evidence_date(record, key):
    value = _evidence_text(record, key, limit=10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Invalid evidence {key}")
    date.fromisoformat(value)
    return value


def _evidence_sources(records):
    if not isinstance(records, list) or not 1 <= len(records) <= 20:
        raise ValueError("Evidence requires a bounded source list")
    projected = []
    for source in _sources(records):
        projected.append(
            {
                key: value
                for key, value in source.items()
                if isinstance(value, str) and len(value) <= 2048
            }
        )
    if not projected:
        raise ValueError("Evidence requires a public source")
    return projected


def _evidence_block(record):
    chart = record["chart"]
    result = {
        "kind": "figure",
        "chart": chart,
        "id": _evidence_text(record, "id", limit=100),
        "caption": _evidence_text(record, "caption", limit=1200),
        "source": _evidence_text(record, "source", limit=1200),
        "sources": _evidence_sources(record.get("sources")),
    }
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", result["id"]):
        raise ValueError("Evidence identifiers must be URL slugs")
    notes = record.get("notes")
    if (
        not isinstance(notes, list)
        or not 2 <= len(notes) <= 12
        or any(not isinstance(note, str) or not note.strip() or len(note) > 2000 for note in notes)
    ):
        raise ValueError("Evidence requires at least two scope notes")
    result["notes"] = notes[:]
    if any(key in record for key in ("points", "flows", "series", "value", "weight")):
        raise ValueError("Evidence views cannot imply numeric magnitudes")
    if "asOf" in record:
        result["asOf"] = _evidence_date(record, "asOf")
    if "releaseId" in record:
        result["releaseId"] = _evidence_text(record, "releaseId", limit=200)
    key = {"relationships": "relationships", "timeline": "events", "evidenceTable": "rows"}[chart]
    rows = record.get(key)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Evidence requires one to one hundred observations")
    fields = {
        "relationships": ("from", "relationship", "to", "asOf", "detail"),
        "timeline": ("date", "title", "detail"),
        "evidenceTable": ("entity", "role", "asOf", "detail"),
    }[chart]
    projected = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid evidence observation")
        item = {
            field: _evidence_date(row, field)
            if field in {"date", "asOf"}
            else _evidence_text(row, field)
            for field in fields
        }
        item["sources"] = _evidence_sources(row.get("sources"))
        projected.append(item)
    result[key] = projected
    if chart == "evidenceTable":
        columns = record.get("columns")
        if not isinstance(columns, list) or not 1 <= len(columns) <= 4:
            raise ValueError("Invalid evidence columns")
        selected = []
        for column in columns:
            if not isinstance(column, dict):
                raise ValueError("Invalid evidence column")
            name = column.get("key")
            if not isinstance(name, str) or name not in _EVIDENCE_COLUMNS or name in selected:
                raise ValueError("Invalid or repeated evidence column")
            selected.append(name)
        result["columns"] = [
            {"key": column["key"], "label": _evidence_text(column, "label", limit=100)}
            for column in columns
        ]
    return result


def _block(record):
    kind = record.get("kind")
    if kind in _TEXT_BLOCKS:
        return _text_block(record)
    if kind == "image":
        return {"kind": kind, **_image(record)}
    if kind == "pair":
        return {"kind": kind, "images": [_image(image) for image in record.get("images", [])]}
    if kind != "figure":
        raise ValueError("Unsupported article block")
    if record.get("chart") in _EVIDENCE_CHARTS:
        return _evidence_block(record)
    result = _fields(
        record, ("kind", "chart", "caption", "source", "series", "notes", "releaseId", "asOf")
    )
    series = record.get("series") or ["value"]
    if not all(isinstance(key, str) and key not in {"__proto__", "constructor"} for key in series):
        raise ValueError("Invalid chart series")
    if "points" in record:
        result["points"] = [
            _fields(point, ("label", "state", "low", "high", *series)) for point in record["points"]
        ]
    if "flows" in record:
        result["flows"] = [_fields(flow, ("from", "to", "value")) for flow in record["flows"]]
    if "sources" in record:
        result["sources"] = _sources(record["sources"])
    return result


def _documents():
    rows = json.loads(_CONTENT.read_text(encoding="utf-8"))
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)) or any(
        not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", key) for key in ids
    ):
        raise ValueError("Article identifiers must be unique URL slugs")
    return rows


def reader_article(record, *, detail=False):
    """Only named reader fields cross the API boundary."""
    result = _fields(record, CARD_FIELDS)
    if "href" in result:
        result["href"] = _public_url(result["href"])
    if "image" in result:
        result["image"] = _image_url(result["image"])
    if result.get("demonstration"):
        result["kind"] = "Demonstration"
    elif result.get("earlyAccess"):
        result["kind"] = "Early access"
    if detail:
        result["body"] = [_block(block) for block in record.get("body", [])]
        result["highlights"] = list(record.get("highlights", []))
        result["authors"] = []
        for author in record.get("authors", []):
            clean = _fields(author, ("name", "role"))
            if photo := _image_url(author.get("photo")):
                clean["photo"] = photo
            result["authors"].append(clean)
        result["sources"] = _sources(record.get("sources", []))
    return result


def article_cards():
    return [reader_article(row) for row in _documents() if not row.get("demonstration")]


def article_detail(slug):
    for row in _documents():
        if row["id"] == slug and row.get("hosted") and not row.get("demonstration"):
            return reader_article(row, detail=True)
    return None
