"""Validate pinned PLOT map evidence and provide bounded outline presentation."""

import math

from cedar_press import repository


def present(value, *, release_id, component, scope, source_rows, selected):
    def refuse():
        raise repository.FullReleaseUnavailable("PLOT map differs from its permitted sample")

    if (
        component not in {"tract_observations", "ownership_observations"}
        or value.get("type") != "FeatureCollection"
        or value.get("collection") != "plot"
        or value.get("component") != component
        or value.get("release_id") != release_id
        or value.get("scope") != scope
        or value.get("source_rows") != source_rows
        or value.get("crs") != "OGC:CRS84"
        or value.get("axis_order") != "longitude,latitude"
    ):
        refuse()
    features = value.get("features")
    if not isinstance(features, list) or len(features) > 30:
        refuse()
    samples = {item["release_row_sha256"]: item for item in selected}
    seen, outlines = set(), []
    for feature in features:
        properties = feature.get("properties", {})
        item = samples.get(properties.get("release_row_sha256"))
        if (
            not item
            or feature.get("type") != "Feature"
            or feature.get("id") != item["row"].get("plot_record_id")
            or feature["id"] in seen
            or properties.get("source_part") != item["source_part"]
            or properties.get("ownership_inference_permitted") is not False
            or properties.get("entity_link") is not None
            or properties.get("crs") != "OGC:CRS84"
        ):
            refuse()
        seen.add(feature["id"])
        geometry = feature.get("geometry", {})
        kind, coordinates = geometry.get("type"), geometry.get("coordinates")
        if kind not in {"Polygon", "MultiPolygon"} or not isinstance(coordinates, list):
            refuse()
        polygons = [coordinates] if kind == "Polygon" else coordinates
        points, paths = [], []
        for polygon in polygons:
            if not isinstance(polygon, list) or not polygon:
                refuse()
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    refuse()
                commands = []
                for point in ring:
                    if (
                        not isinstance(point, list)
                        or len(point) != 2
                        or any(type(n) not in {int, float} or not math.isfinite(n) for n in point)
                        or not -180 <= point[0] <= 180
                        or not -90 <= point[1] <= 90
                    ):
                        refuse()
                    points.append(point)
                    if len(points) > 10000:
                        refuse()
                    # Longitude horizontally; invert latitude for SVG's downward y.
                    commands.append(f"{'M' if len(commands) == 0 else 'L'}{point[0]} {-point[1]}")
                paths.append(" ".join(commands) + " Z")
        if not points:
            refuse()
        west, east = min(p[0] for p in points), max(p[0] for p in points)
        south, north = min(p[1] for p in points), max(p[1] for p in points)
        width, height = east - west, north - south
        # No invented wrap across the date line and no distance/area inference.
        drawable = 0 < width <= 180 and height > 0
        pad = max(width, height) * 0.05
        outlines.append(
            {
                "id": feature["id"],
                "path": " ".join(paths) if drawable else None,
                "view_box": f"{west - pad} {-north - pad} {width + 2 * pad} {height + 2 * pad}",
                "bbox": [west, south, east, north],
                "source": item["source"],
                "release_row_sha256": item["release_row_sha256"],
            }
        )
    return {**value, "outlines": outlines}
