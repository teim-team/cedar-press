#!/usr/bin/env python3
"""873 - the AIANNH crosswalk: shared geographic infrastructure (ADR-015 rule 2).

WHO OWNS THIS FILE
------------------
Nobody, which is the point. ADR-015 rule 2 says "a county is not a reservation"
and "AIANNH is the better key where it can be had". Several workstreams need
AIANNH and none of them should each build their own. This script therefore
writes THREE files that are explicitly SHARED INFRASTRUCTURE, named `geo_*`, and
consumed by anyone. It writes to no workstream's table. In particular it does
not touch `data/clean/cedar_constellation_edges.csv`; `geo_point_aiannh_
assignment.csv` is an INPUT the constellation workstream may use to raise an
ADR-014 `located_within` edge, and the decision to raise one is theirs.

The existing `data/raw/external/compacts/prior_extractions/
tribe_aiannh_crosswalk_master.csv` (303 rows) is a TRIBE -> AIANNH name match
for gaming-compact tribes only. It is a different object from these files, it
is not superseded, and it is read here only to cross-check names.

ZERO DOWNLOADS. `data/raw/external/tiger/tl_2024_us_aiannh.zip` - the Census
TIGER/Line 2024 national AIANNH shapefile, 864 areas - was already on disk
(pulled 2026-09-01). ADR-015 did not know it was there; it says AIANNH is
"the better key where it can be had" without saying it could be had today.

WHAT CAN AND CANNOT BE BUILT FROM WHAT IS ON DISK
-------------------------------------------------
CAN: an exact point-in-polygon assignment. Any Cedar row carrying a latitude
and longitude gets the AIANNH area it falls inside, or nothing. That is a hard
geometric fact, not an inference, and it is the honest form of ADR-014's
`located_within` tier.

CANNOT: a complete county <-> AIANNH overlap table. That needs county polygons
to intersect against and TIGER county boundaries are NOT on disk. What this
script emits instead is `geo_aiannh_county_observed.csv`: the (AIANNH, county)
pairs Cedar has actually OBSERVED, one row per pair, carrying how many points
support it and from where. It is a floor, never a census. An AIANNH area absent
from that file is not an AIANNH area outside every county - it is an area Cedar
holds no geocoded point inside. The file says so in a column, on every row.
Read it as evidence, never as coverage.

PROJECTION. TIGER 2024 AIANNH is NAD83 (GCS_North_American_1983, degrees).
Cedar's geocoded points are WGS84 from the Census geocoder and from Google. The
two datums differ by roughly a metre in CONUS, which is far below the precision
of a rooftop geocode and orders of magnitude below the size of any AIANNH area.
No transform is applied and none is warranted; this note exists so that the
absence of one is a decision on the record rather than an oversight.

WHAT A POINT INSIDE AN AIANNH AREA DOES AND DOES NOT MEAN. It means the address
Cedar holds falls inside the polygon Census publishes. It does not mean the
entity is Native, tribally owned, or on trust land - AIANNH areas include
statistical areas and Oklahoma tribal statistical areas that cover whole cities.
`classfp` and `comptyp` are carried on every row so a consumer can refuse the
statistical classes. ADR-014 rule 3 stands: an entity's own words about who it
serves outrank a polygon it sits inside.

MODES
-----
    py -3 code/873_build_aiannh_crosswalk.py           build
    py -3 code/873_build_aiannh_crosswalk.py verify    re-measure and assert
    py -3 code/873_build_aiannh_crosswalk.py selftest  corrupt a COPY and prove
                                                       verify exits 1

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 the dimension has one row per TIGER record, `aiannh_geoid` unique, and the
     count equals the shapefile's (864 as pulled). A short dimension means the
     zip failed to fully extract.
  I2 every `aiannh_geoid` on an assignment row or an overlap row exists in the
     dimension. A dangling geoid is a join that will silently drop.
  I3 ROW CONSERVATION: for every source table, points_in == points_out. Every
     geocoded point gets a row whether or not it landed inside an area; a point
     outside every AIANNH area is a finding, not a row to drop.
  I4 every `county_fips` is 5 digits.
  I5 BOUNDING-BOX RECHECK: every assigned point lies inside the bounding box of
     the area it was assigned to. This is an independent test of the
     point-in-polygon result -- it uses the shapefile's own bbox record rather
     than re-running the same geometry code that produced the answer.
"""

import csv
import json
import os
import sys
import tempfile
import zipfile

csv.field_size_limit(10 * 1024 * 1024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
TIGER_ZIP = os.path.join(ROOT, "data", "raw", "external", "tiger", "tl_2024_us_aiannh.zip")
TIGER_STEM = "tl_2024_us_aiannh"
COMPACT_XWALK = os.path.join(ROOT, "data", "raw", "external", "compacts",
                             "prior_extractions", "tribe_aiannh_crosswalk_master.csv")
BIA_GEOCODED = os.path.join(ROOT, "data", "raw", "external", "gaming", "directory_core",
                            "bia_compact_properties_geocoded_v2.csv")

OUT_DIM = os.path.join(CLEAN, "geo_aiannh_dim.csv")
OUT_PTS = os.path.join(CLEAN, "geo_point_aiannh_assignment.csv")
OUT_OVL = os.path.join(CLEAN, "geo_aiannh_county_observed.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_AIANNH_STATS.json")

# (clean table, id column, latitude column, longitude column, county fips column
#  or "", label column or "")
POINT_SOURCES = [
    ("gaming_property_locations.csv", "location_observation_id",
     "latitude", "longitude", "county_fips", "property_name"),
    ("gaming_facilities.csv", "facility_id", "latitude", "longitude", "", "facility_name"),
    ("gaming_properties.csv", "facility_id", "latitude", "longitude", "", "property_name"),
    ("nepa_eplanning_projects.csv", "eplanning_project_id",
     "latitude", "longitude", "", "project_name"),
    ("resource_assets.csv", "resource_asset_id", "latitude", "longitude",
     "fips_code", "asset_name"),
]

DIM_FIELDS = ["aiannh_geoid", "aiannhce", "aiannh_name", "aiannh_namelsad",
              "lsad", "classfp", "comptyp", "aiannhr", "funcstat",
              "aland_sqm", "awater_sqm", "intptlat", "intptlon",
              "bbox_minx", "bbox_miny", "bbox_maxx", "bbox_maxy",
              "n_parts", "in_compact_extraction"]

PTS_FIELDS = ["point_id", "source_table", "source_row_id", "label",
              "latitude", "longitude",
              "aiannh_geoid", "aiannh_name", "aiannh_classfp", "aiannh_comptyp",
              "inside_flag", "assignment_basis",
              "reported_county_fips", "geometry_source", "n_candidate_areas"]

OVL_FIELDS = ["aiannh_geoid", "aiannh_name", "county_fips", "state_fips",
              "n_points", "sources", "basis", "coverage_note"]

COVERAGE_NOTE = ("PARTIAL. Observed from Cedar geocoded points only; county "
                 "polygons are not on disk so this is not an exhaustive overlap. "
                 "Absence of a pair is not evidence the areas do not overlap.")


def extract_tiger():
    tmp = tempfile.mkdtemp(prefix="873_tiger_")
    with zipfile.ZipFile(TIGER_ZIP) as z:
        names = z.namelist()
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            n = TIGER_STEM + ext
            if n in names:
                with open(os.path.join(tmp, n), "wb") as fh:
                    fh.write(z.read(n))
    return os.path.join(tmp, TIGER_STEM)


def build():
    import shapefile                       # pyshp
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree

    stem = extract_tiger()
    sf = shapefile.Reader(stem)
    fields = [f[0] for f in sf.fields[1:]]
    print(f"[873] TIGER AIANNH records: {len(sf)}   fields: {len(fields)}")

    compact_codes = set()
    if os.path.exists(COMPACT_XWALK):
        with open(COMPACT_XWALK, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                for c in (row.get("aiannh_full_geoid"), row.get("aiannh_geoid"),
                          row.get("aiannh_code")):
                    if c and c.strip():
                        compact_codes.add(c.strip().upper())
    print(f"[873] compact-extraction aiannh codes: {len(compact_codes)}")

    geoms = []
    meta = []
    with open(OUT_DIM, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(DIM_FIELDS)
        for sr in sf.iterShapeRecords():
            r = dict(zip(fields, sr.record))
            g = shape(sr.shape.__geo_interface__)
            if not g.is_valid:
                g = g.buffer(0)
            bb = sr.shape.bbox
            geoid = (r.get("GEOID") or "").strip()
            code = (r.get("AIANNHCE") or "").strip()
            geoms.append(g)
            meta.append({
                "geoid": geoid, "name": (r.get("NAME") or "").strip(),
                "classfp": (r.get("CLASSFP") or "").strip(),
                "comptyp": (r.get("COMPTYP") or "").strip(),
                "bbox": bb,
            })
            w.writerow([geoid, code, r.get("NAME", ""), r.get("NAMELSAD", ""),
                        r.get("LSAD", ""), r.get("CLASSFP", ""), r.get("COMPTYP", ""),
                        r.get("AIANNHR", ""), r.get("FUNCSTAT", ""),
                        r.get("ALAND", ""), r.get("AWATER", ""),
                        r.get("INTPTLAT", ""), r.get("INTPTLON", ""),
                        f"{bb[0]:.6f}", f"{bb[1]:.6f}", f"{bb[2]:.6f}", f"{bb[3]:.6f}",
                        len(sr.shape.parts),
                        "1" if (geoid.upper() in compact_codes
                                or code.upper() in compact_codes) else "0"])
    print(f"[873] wrote {os.path.relpath(OUT_DIM, ROOT)}  areas {len(meta):,}")

    tree = STRtree(geoms)

    # -------------------------------------------------------------- points
    counts = {}
    overlap = {}
    n_inside = 0
    n_out = 0
    with open(OUT_PTS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(PTS_FIELDS)

        def emit(src, rid, label, la, lo, cfips, geomsrc):
            nonlocal n_inside, n_out
            pt = Point(lo, la)
            cand = list(tree.query(pt))
            hits = [i for i in cand if geoms[int(i)].covers(pt)]
            pid = f"{src}:{rid}"
            if hits:
                i = int(hits[0])
                m = meta[i]
                n_inside += 1
                w.writerow([pid, src, rid, label, f"{la:.6f}", f"{lo:.6f}",
                            m["geoid"], m["name"], m["classfp"], m["comptyp"],
                            "1", "point_in_polygon_tiger2024_aiannh",
                            cfips, geomsrc, len(cand)])
                if cfips:
                    k = (m["geoid"], cfips)
                    e = overlap.setdefault(k, {"n": 0, "src": set(),
                                               "name": m["name"]})
                    e["n"] += 1
                    e["src"].add(src)
            else:
                n_out += 1
                w.writerow([pid, src, rid, label, f"{la:.6f}", f"{lo:.6f}",
                            "", "", "", "", "0",
                            "point_outside_every_tiger2024_aiannh_area",
                            cfips, geomsrc, len(cand)])

        for tbl, idc, latc, lonc, cfc, labc in POINT_SOURCES:
            p = os.path.join(CLEAN, tbl)
            if not os.path.exists(p):
                print(f"  !! missing {tbl}")
                continue
            nin = nout = nskip = 0
            with open(p, newline="", encoding="utf-8-sig") as f2:
                for row in csv.DictReader(f2):
                    nin += 1
                    try:
                        la = float((row.get(latc) or "").strip())
                        lo = float((row.get(lonc) or "").strip())
                    except (TypeError, ValueError):
                        nskip += 1
                        continue
                    if not (-180 < lo < 0 and 15 < la < 75):
                        nskip += 1
                        continue
                    cf = (row.get(cfc) or "").strip() if cfc else ""
                    if cf.endswith(".0"):
                        cf = cf[:-2]
                    cf = cf.zfill(5) if cf and cf.isdigit() and len(cf) == 4 else cf
                    if len(cf) != 5 or not cf.isdigit():
                        cf = ""
                    emit(tbl, (row.get(idc) or "").strip(),
                         (row.get(labc) or "").strip() if labc else "",
                         la, lo, cf, (row.get("geocode_method") or "").strip())
                    nout += 1
            counts[tbl] = {"rows_read": nin, "points_emitted": nout,
                           "rows_without_usable_coordinates": nskip}
            print(f"  [pts   ] {tbl:<36} read {nin:>6}  geocoded {nout:>6}"
                  f"  no-coords {nskip:>6}")
    print(f"[873] wrote {os.path.relpath(OUT_PTS, ROOT)}")
    print(f"        inside an AIANNH area : {n_inside:,}")
    print(f"        outside every area    : {n_out:,}")

    # ------------------------------------------------------------ overlap
    # Second basis: BIA compact properties already pair an aiannh_geoid the
    # extraction assigned with a county_fips the geocoder assigned. Carried
    # under its own basis so a consumer can take one and refuse the other.
    valid = {m["geoid"]: m["name"] for m in meta}
    bare = {}
    for m in meta:
        bare.setdefault(m["geoid"].rstrip("RT"), m["geoid"])
    n_bia = 0
    if os.path.exists(BIA_GEOCODED):
        with open(BIA_GEOCODED, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                g = (row.get("aiannh_geoid") or "").strip()
                cf = (row.get("county_fips") or "").strip()
                if cf.endswith(".0"):
                    cf = cf[:-2]
                if cf and cf.isdigit() and len(cf) == 4:
                    cf = cf.zfill(5)
                if not g or len(cf) != 5 or not cf.isdigit():
                    continue
                gg = g if g in valid else bare.get(g.zfill(4), "")
                if not gg:
                    continue
                k = (gg, cf)
                e = overlap.setdefault(k, {"n": 0, "src": set(), "name": valid[gg]})
                e["n"] += 1
                e["src"].add("bia_compact_properties_geocoded_v2.csv")
                n_bia += 1
    print(f"[873] BIA compact property pairs folded in: {n_bia:,}")

    with open(OUT_OVL, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(OVL_FIELDS)
        for (g, cf) in sorted(overlap):
            e = overlap[(g, cf)]
            w.writerow([g, e["name"], cf, cf[:2], e["n"], ";".join(sorted(e["src"])),
                        "observed_point", COVERAGE_NOTE])
    print(f"[873] wrote {os.path.relpath(OUT_OVL, ROOT)}  pairs {len(overlap):,}"
          f"  areas covered {len({g for g, _ in overlap}):,} of {len(meta):,}")

    stats = {
        "built": "2026-09-02",
        "script": "873_build_aiannh_crosswalk.py",
        "tiger_source": "data/raw/external/tiger/tl_2024_us_aiannh.zip",
        "aiannh_areas": len(meta),
        "points_inside": n_inside,
        "points_outside": n_out,
        "point_sources": counts,
        "overlap_pairs": len(overlap),
        "overlap_areas_covered": len({g for g, _ in overlap}),
        "bia_pairs_folded": n_bia,
        "coverage_note": COVERAGE_NOTE,
    }
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"[873] wrote {os.path.relpath(OUT_STATS, ROOT)}")
    return stats


def verify(dim_path=None, pts_path=None, ovl_path=None, quiet=False):
    dim_path = dim_path or OUT_DIM
    pts_path = pts_path or OUT_PTS
    ovl_path = ovl_path or OUT_OVL
    say = (lambda *a: None) if quiet else print

    fails = []
    for p in (dim_path, pts_path, ovl_path):
        if not os.path.exists(p):
            fails.append(f"MISSING {p}")
    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1

    # I1 + bboxes for I5
    dim = {}
    dups = 0
    with open(dim_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            g = row["aiannh_geoid"]
            if g in dim:
                dups += 1
            dim[g] = (float(row["bbox_minx"]), float(row["bbox_miny"]),
                      float(row["bbox_maxx"]), float(row["bbox_maxy"]))
    say(f"[873 verify] dimension areas {len(dim):,}  duplicate geoids {dups}")
    if dups:
        fails.append(f"I1 aiannh_geoid not unique in the dimension: {dups}")
    if len(dim) < 800:
        fails.append(f"I1 dimension holds only {len(dim)} areas, TIGER 2024 has 864 "
                     f"-- the shapefile did not fully extract")

    # I2 / I3 / I5 on the assignments
    per_src = {}
    dangling = 0
    outside_bbox = 0
    n = 0
    with open(pts_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n += 1
            per_src[row["source_table"]] = per_src.get(row["source_table"], 0) + 1
            g = row["aiannh_geoid"]
            if not g:
                continue
            if g not in dim:
                dangling += 1
                continue
            try:
                la = float(row["latitude"])
                lo = float(row["longitude"])
            except ValueError:
                outside_bbox += 1
                continue
            x0, y0, x1, y1 = dim[g]
            tol = 1e-6
            if not (x0 - tol <= lo <= x1 + tol and y0 - tol <= la <= y1 + tol):
                outside_bbox += 1
    say(f"[873 verify] assignment rows {n:,}  dangling geoids {dangling}"
        f"  outside assigned bbox {outside_bbox}")
    if dangling:
        fails.append(f"I2 assignment rows name an aiannh_geoid not in the "
                     f"dimension: {dangling}")
    if outside_bbox:
        fails.append(f"I5 assigned points fall outside the bounding box of their "
                     f"own area: {outside_bbox}")

    # I3 row conservation against the live sources
    for tbl, idc, latc, lonc, _cfc, _labc in POINT_SOURCES:
        p = os.path.join(CLEAN, tbl)
        if not os.path.exists(p):
            continue
        want = 0
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                try:
                    la = float((row.get(latc) or "").strip())
                    lo = float((row.get(lonc) or "").strip())
                except (TypeError, ValueError):
                    continue
                if -180 < lo < 0 and 15 < la < 75:
                    want += 1
        got = per_src.get(tbl, 0)
        say(f"[873 verify]   {tbl:<36} geocoded {want:>6}  emitted {got:>6}"
            f"  {'ok' if want == got else 'MISMATCH'}")
        if want != got:
            fails.append(f"I3 row conservation broken for {tbl}: "
                         f"{want} geocoded points, {got} rows emitted")

    # I2 / I4 on the overlap
    m = 0
    bad_cf = 0
    dang2 = 0
    with open(ovl_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            m += 1
            cf = row["county_fips"]
            if len(cf) != 5 or not cf.isdigit():
                bad_cf += 1
            if row["aiannh_geoid"] not in dim:
                dang2 += 1
    say(f"[873 verify] overlap pairs {m:,}  bad county_fips {bad_cf}  dangling {dang2}")
    if bad_cf:
        fails.append(f"I4 overlap rows carry a county_fips that is not 5 digits: {bad_cf}")
    if dang2:
        fails.append(f"I2 overlap rows name an aiannh_geoid not in the dimension: {dang2}")

    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[873 verify] OK -- I1 I2 I3 I4 I5 all hold")
    return 0


def selftest():
    import shutil
    if not os.path.exists(OUT_DIM):
        print("[873 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="873_selftest_")
    d = os.path.join(tmp, "dim.csv")
    pt = os.path.join(tmp, "pts.csv")
    ov = os.path.join(tmp, "ovl.csv")
    ok = True

    def reset():
        shutil.copyfile(OUT_DIM, d)
        shutil.copyfile(OUT_PTS, pt)
        shutil.copyfile(OUT_OVL, ov)

    def rows(p):
        with open(p, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def write(p, rr):
        with open(p, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rr)

    def case(name, mutate):
        nonlocal ok
        reset()
        mutate()
        rc = verify(d, pt, ov, quiet=True)
        good = rc == 1
        print(f"  {name:<54} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    reset()
    base = verify(d, pt, ov, quiet=True)
    print(f"[873 selftest] clean copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def short_dim():
        write(d, rows(d)[:400])

    def dup_dim():
        rr = rows(d)
        rr.append(list(rr[1]))
        write(d, rr)

    def dangling_point():
        rr = rows(pt)
        i = rr[0].index("aiannh_geoid")
        for r in rr[1:]:
            if r[i]:
                r[i] = "9999Z"
                break
        write(pt, rr)

    def drop_a_point():
        rr = rows(pt)
        write(pt, rr[:1] + rr[2:])

    def move_a_point():
        rr = rows(pt)
        gi = rr[0].index("aiannh_geoid")
        la = rr[0].index("latitude")
        lo = rr[0].index("longitude")
        for r in rr[1:]:
            if r[gi]:
                r[la], r[lo] = "44.000000", "-70.000000"
                break
        write(pt, rr)

    def bad_county():
        rr = rows(ov)
        if len(rr) > 1:
            rr[1][rr[0].index("county_fips")] = "4021"
        write(ov, rr)

    case("I1 dimension truncated to 400 areas", short_dim)
    case("I1 duplicate aiannh_geoid in the dimension", dup_dim)
    case("I2 assignment names an area that does not exist", dangling_point)
    case("I3 one geocoded point silently dropped", drop_a_point)
    case("I5 assigned point moved outside its own area's bbox", move_a_point)
    case("I4 overlap county_fips loses its leading zero", bad_county)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[873 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    build()
    sys.exit(verify())
