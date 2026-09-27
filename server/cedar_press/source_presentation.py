"""Readable citations from permitted rows; original publishers are never file names.

The browser and release service share the maintained mapping JSON. This module
does not establish publication rights, identity or the completeness of a source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[2] / "data/cedar"
SPEC = json.loads((ROOT / "source_presentation.json").read_text(encoding="utf-8"))
REGISTERED = json.loads((ROOT / "source_display.json").read_text(encoding="utf-8"))["sources"]


def readable(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        return None
    if re.search(r"[\x00-\x1f]|[A-Za-z]:[\\/]|file://|\\\\|^[/~]", value):
        return None
    return value.strip()


def source_title(value):
    title = readable(value)
    return (
        title
        if title and not re.search(r"\.(csv|parquet|jsonl?|xlsx?|zip|pdf)$", title, re.I)
        else None
    )


def safe_url(value):
    if not isinstance(value, str) or re.search(r"[\s\\\x00-\x1f]", value):
        return None
    try:
        url = urlsplit(value)
        host = (url.hostname or "").lower()
        if (
            url.scheme not in {"http", "https"}
            or url.username
            or url.password
            or "." not in host
            or host == "localhost"
            or re.search(r"\.(local|localhost|internal|test|invalid)$", host)
            or re.fullmatch(r"[\d.]+", host)
            or ":" in host
        ):
            return None
        if any(
            re.fullmatch(
                r"api[_-]?key|access[_-]?token|token|password|signature|sig|credential|x-amz-.*",
                key,
                re.I,
            )
            for key, _ in parse_qsl(url.query)
        ):
            return None
        return value
    except ValueError:
        return None


def present(collection, row, component=None):
    """Call only after the exact release/component and field-rights gates pass."""
    spec = (
        SPEC["gaming_components"].get(component)
        if collection == "gaming"
        else SPEC["collections"].get(collection)
    )
    if not spec or any(
        re.match(r"^(held|withheld|contested|restricted|internal_)", str(row.get(k, "")), re.I)
        for k in ("publication_status", "publication_rights_status", "rights_class")
    ):
        return None
    family = SPEC["plot_sources"].get(row.get("source_id")) if collection == "plot" else None
    registered = REGISTERED.get(collection + "/" + str(row.get("source_id")), {})
    publisher = (
        (family[0] if family else None) or registered.get("publisher") or spec.get("publisher")
    )
    publisher = (
        publisher
        or source_title(row.get(spec.get("publisherField")))
        or spec.get("systems", {}).get(row.get("source_system"))
    )
    mapped_title = spec.get("titlesByDocument", {}).get(row.get(spec.get("documentTitleField")))
    title = (
        (family[1] if family else None)
        or source_title(row.get(spec.get("title")))
        or mapped_title
        or registered.get("source_title")
        or spec.get("dataset")
    )
    title_basis = (
        "Source dataset title"
        if family
        else spec.get("titleBasis")
        or (
            "Report title"
            if mapped_title
            else "Registered source title"
            if registered
            else "Source dataset"
        )
    )
    urls = spec.get(
        "urls", ["source_record_url", "source_url", "evidence_url", "fr_notice_url", "url"]
    )
    url = next((safe_url(row.get(k)) for k in urls if safe_url(row.get(k))), None)
    publisher = publisher or SPEC.get("publishers_by_host", {}).get(
        urlsplit(url).hostname if url else None
    )

    def fields(names):
        return {name: readable(row.get(name)) for name in names or [] if readable(row.get(name))}

    period = fields(spec.get("periods"))
    locators = fields(spec.get("locators"))
    period_text = "; ".join(key.replace("_", " ") + ": " + value for key, value in period.items())
    gaps = []
    if not publisher:
        gaps.append("Original publisher has not been established for this record.")
    if not title or title_basis in {"Cedar event description", "Registered source title"}:
        gaps.append("Original report or page title is not recorded.")
    if not url:
        gaps.append("A public source URL is not recorded.")
    gaps.append(
        "A release hash identifies transformed data; "
        "it does not substitute for an original document hash."
    )
    citation = ". ".join(
        str(x)
        for x in [
            publisher or "Publisher not established",
            title_basis + ": " + title if title else None,
            "; ".join(locators.values()),
            period_text,
            url,
        ]
        if x
    )
    return {
        "publisher": publisher,
        "title": title,
        "titleBasis": title_basis,
        "url": url,
        "reportingPeriod": period,
        "periodText": period_text,
        "eventDates": fields(spec.get("events")),
        "locators": locators,
        "publicationDate": next(
            (
                readable(row.get(k))
                for k in spec.get("publishedFields", [spec.get("published")])
                if readable(row.get(k))
            ),
            None,
        ),
        "snapshotDate": readable(row.get(spec.get("snapshot"))),
        "citation": citation,
        "gaps": gaps,
    }
