"""One customer CSV per collection, assembled only from the existing verified download path.

The table follows the owner's rules of 2026-10-04 (Elijah Moreno), shared with the
producer in ``customer_sheet`` (vendored byte for byte from Lumecon-data): one flat
table at the collection's declared grain; Cedar IDs and every dataset and public
registry identifier kept, only proprietary identifiers (DUNS, Casino City)
removed (owner correction 2026-10-04); public sources only; no version labels.
Every component is still read through the pinned, byte-verified download path; the
rules apply only to what is presented.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
from contextlib import closing

from cedar_press import csv_safety, customer_sheet
from cedar_press import repository as r


def _tables(collection, pin, manifest):
    """Every permitted, contract-consistent table of the pinned release."""
    tables = {}
    logical = {entry["name"]: entry for entry in manifest.get("partitioned_components", [])}
    for name in r.grove_components(collection):
        parts = (
            [part["component"] for part in logical[name]["parts"]] if name in logical else [name]
        )
        if any(part not in manifest["components"] for part in parts):
            continue
        try:
            descriptor = r._grove_component_release(pin, manifest, name, metadata_only=True)
        except r.ComponentPublicationHeld:
            continue
        contract = manifest["components"][parts[0]]
        for part in parts:
            candidate = manifest["components"][part]
            if any(
                candidate.get(key) != contract.get(key)
                for key in (
                    "row_grain",
                    "fields",
                    "primary_key",
                    "rights",
                    "publication_status_field",
                )
            ) or candidate.get("status_value_fields", []) != contract.get(
                "status_value_fields", []
            ):
                raise r.FullReleaseUnavailable("Spreadsheet partition meanings disagree")
        tables[name] = {"contract": contract, "descriptor": descriptor}
    if not tables:
        raise r.FullReleaseUnavailable("No permitted spreadsheet records")
    return tables


def _layout(collection, tables):
    try:
        layout = customer_sheet.choose_layout(collection, tables)
    except customer_sheet.LayoutError as error:
        raise r.FullReleaseUnavailable("No customer table for this release") from error
    used = list(dict.fromkeys([*layout["main"]["tables"], *(a["table"] for a in layout["attach"])]))
    sheet = customer_sheet.plan(
        collection, {name: tables[name]["contract"]["fields"] for name in used}, layout
    )
    return layout, sheet


def metadata(collection):
    """Advertise a single file only when the pinned collection can be verified."""
    try:
        return download(collection, metadata_only=True)
    except (r.FullReleaseUnavailable, OSError, ValueError, KeyError, TypeError):
        return None


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    text = str(value)
    # Only text can be a formula; a typed number is written as itself.
    return csv_safety.spreadsheet_safe(text) if isinstance(value, str) else text


def _origin(contract):
    source = contract.get("source")
    return customer_sheet.public_origin(source.get("url") if isinstance(source, dict) else None)


def _spool(collection, layout, sheet, rows, origins):
    """Write the one customer table to a private spool; the caller owns it."""
    output = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 - response owns this spool
    digest = hashlib.sha256()

    def write(values):
        line = io.StringIO(newline="")
        csv.writer(line, lineterminator="\n").writerow([_cell(value) for value in values])
        content = line.getvalue().encode("utf-8")
        output.write(content)
        digest.update(content)

    try:
        header, records, report = customer_sheet.flatten(collection, layout, sheet, rows, origins)
        write(header)
        with closing(records):
            for record in records:
                write(record.get(column) for column in header)
        output.seek(0)
        return output, digest.hexdigest(), report
    except BaseException:
        output.close()
        raise


def download(collection, release_id=None, *, metadata_only=False):
    """Pins and every component's byte, schema, key and rights checks stay binding."""
    if collection != "need":
        r.assert_collection_publishable(collection)
    if not r.is_component_release(collection):
        return _single_dataset(collection, release_id, metadata_only=metadata_only)
    pin = r.grove_release_pin(collection)
    if not metadata_only and pin["release_id"] != release_id:
        raise r.FullReleaseUnavailable("Requested release is not the approved catalog pin")
    r._grove_catalog(pin)
    manifest = r._grove_manifest(pin)
    r.assert_collection_publishable(
        collection, manifest=manifest, component=r.need_publication.COMPONENT
    )
    tables = _tables(collection, pin, manifest)
    layout, sheet = _layout(collection, tables)
    main = layout["main"]["tables"]
    descriptor = {
        "kind": "spreadsheet",
        "format": "csv",
        "release_id": pin["release_id"],
        "manifest_sha256": pin["manifest_sha256"],
        **r.need_publication.descriptor_metadata(manifest, r.need_publication.COMPONENT),
        "fields": list(sheet["columns"]),
        "record_count": sum(tables[name]["descriptor"]["record_count"] for name in main),
        "filename": f"{collection}.csv",
        "scope": layout["grain"] or "One record per row.",
        "download_path": (
            f"/press/collections/{collection}/spreadsheet-download?release_id={pin['release_id']}"
        ),
    }
    if metadata_only:
        return descriptor

    def rows(name):
        part = r._grove_component_release(pin, manifest, name)
        with closing(part["content_file"]) as content:
            for line in content:
                # Owner ruling 2026-10-04 (Elijah Moreno): a held, contested
                # or withheld status is shown, not dropped.
                yield json.loads(line)

    origins = {name: _origin(table["contract"]) for name, table in tables.items()}
    output, digest, report = _spool(collection, layout, sheet, rows, origins)
    if report["counts"]["rows"] != descriptor["record_count"]:
        output.close()
        raise r.FullReleaseUnavailable("Spreadsheet count differs from verified records")
    return {
        **descriptor,
        "content_file": output,
        "record_count": report["counts"]["rows"],
        "sha256": digest,
        "media_type": "text/csv; charset=utf-8",
        "customer_sheet": report,
        "citation": r.launch.collection_citation(collection)
        or f"Lumecon, {collection}, Cedar collection.",
    }


def _single_dataset(collection, release_id, *, metadata_only):
    """A flagship is one table already; it gets the same presentation rules."""
    source = r.full_release(collection, release_id, metadata_only=metadata_only)
    rid = source["release_id"]
    fields = [{"name": name, "type": "string"} for name in source["fields"]]
    layout = customer_sheet.choose_layout(collection, ["records"])
    sheet = customer_sheet.plan(collection, {"records": fields}, layout)
    descriptor = {
        "kind": "spreadsheet",
        "format": "csv",
        "release_id": rid,
        "fields": list(sheet["columns"]),
        "record_count": source["record_count"],
        "filename": f"{collection}.csv",
        "scope": source.get("scope", "One source observation per row."),
        "download_path": f"/press/collections/{collection}/spreadsheet-download?release_id={rid}",
    }
    if metadata_only:
        return descriptor
    content = source.get("content_file") or source.get("spool") or io.BytesIO(source["content"])

    def rows(_name):
        with closing(content):
            for line in content:
                yield json.loads(line)

    output, digest, report = _spool(collection, layout, sheet, rows, {})
    if report["counts"]["rows"] != source["record_count"]:
        output.close()
        raise r.FullReleaseUnavailable("Spreadsheet count differs from verified records")
    return {
        **descriptor,
        "content_file": output,
        "record_count": report["counts"]["rows"],
        "sha256": digest,
        "media_type": "text/csv; charset=utf-8",
        "customer_sheet": report,
        "citation": source["citation"],
    }


def preview_table(collection, fields, values):
    """A bounded preview of the customer table: header and CSV cells, row by row.

    ``fields`` and ``values`` map each presented table to its field definitions
    and rows. Related detail is summarized from the full release only, so a
    preview built from a few rows leaves those columns out rather than showing
    blanks that read as measured absences.
    """
    layout = {**customer_sheet.choose_layout(collection, fields), "attach": []}
    plan = customer_sheet.plan(collection, fields, layout)
    header, records, _report = customer_sheet.flatten(
        collection, layout, plan, lambda name: iter(values[name]), {}
    )
    with closing(records):
        return header, [[_cell(record.get(name)) for name in header] for record in records]


_PACKAGING = ("record_type", "record_key", "record_grain")


def _declared_orders(collection):
    """Contract column orders for a sample written in the earlier appended layout.

    That layout sorted columns by name. NEED's reviewed table keeps its proof
    contract's order; a flagship keeps the owner's approved public order in
    ``data/cedar/field_map.json`` (2026-09-05); a governed component keeps its
    declaration's order.
    """
    from cedar_press import governed_collections

    orders = {r.need_publication.COMPONENT: list(r.need_publication.CLAIM_FIELDS)}
    for name, declared in governed_collections.component_declarations(collection).items():
        orders[name] = [field.get("column") or field.get("name") for field in declared["fields"]]
    for table in r._field_map_tables().values():
        if table.get("collection") == collection and table.get("order"):
            orders.setdefault("*", list(table["order"]))
    return orders


def present_sample(collection, text):
    """A ten-row sample in the earlier appended layout, as the customer table.

    Rows of another grain than the collection's customer table are left out;
    internal keys, version labels, local sources and DUNS never reach the file
    (owner rules 2026-10-04). Related-table columns need the full release, so a
    sample leaves them out rather than showing blanks that read as absences. A
    sample already in customer form passes through the same rules unchanged.
    """
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    if not rows:
        return text
    header = list(rows[0])
    orders = _declared_orders(collection)
    fields, values = {}, {}
    for row in rows:
        table = row.get("record_type") or "records"
        names = [
            name.split("__", 1)[1] if name.startswith(table + "__") else name
            for name in header
            if name not in _PACKAGING and ("__" not in name or name.startswith(table + "__"))
        ]
        if table in orders:
            names = orders[table]  # The table's own contract, in its order.
        elif orders.get("*") and set(orders["*"]) >= set(names):
            names = [name for name in orders["*"] if name in names]
        fields.setdefault(table, [{"name": name, "type": "string"} for name in names])
        declared = [field["name"] for field in fields[table]]
        values.setdefault(table, []).append(
            {name: row.get(f"{table}__{name}", row.get(name)) or None for name in declared}
        )
    columns, cells = preview_table(collection, fields, values)
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(cells)
    return out.getvalue()
