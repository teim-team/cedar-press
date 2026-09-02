#!/usr/bin/env python3
"""
1119 - acquire the BIA's own ArcGIS server, `biamaps.geoplatform.gov`.

    py -3 code/1119_acquire_biamaps_arcgis.py probe     # counts + robots, no bulk
    py -3 code/1119_acquire_biamaps_arcgis.py pull      # raw pages -> data/raw
    py -3 code/1119_acquire_biamaps_arcgis.py build     # raw -> data/clean
    py -3 code/1119_acquire_biamaps_arcgis.py verify    # exits 1 on breach

WHAT THIS IS
------------
Six layers, 250,284 rows, no API key, `robots.txt` returns 404 so nothing is
disallowed for any agent token we plausibly are (checked as a UNION, not with
our own UA - see `code/cedar_arcgis.py`). The host was found by the
2026-09-02 source survey by following `www.bie.edu/schools`, not by searching;
`docs/SOURCE_EXPLORATION_2026-09-02.csv` rates all six ACQUIRE and Cedar's
17-row source registry touches none of them.

WHAT IT WRITES, AND THE GRAIN OF EACH  (declared in `512`, block GRAIN_BIAMAPS)

  data/clean/resource_bia_mineral_acreage_tracts.csv   249,165
      one row per (tract, resource) as the BIA's Land Titles and Records
      offices hold it: `land_area_name` + `tract_id` + `resource_code` +
      `ownership_type`, with `acres`. NOT one row per tract and NOT one row
      per tribe. This is the ACREAGE DENOMINATOR that
      `docs/WHAT_IS_MISSING.md` natural-resources #3 says the revenue table
      has never had.
  data/clean/bia_pl102_477_plans.csv                        84
      one row per PL 102-477 plan agreement, with plan_start_date /
      plan_expiration_date / plan_renewal_date - DATED public facts, which is
      exactly what the 545-entity stale tail needs.
  data/clean/bia_offices.csv                                93
      one row per BIA office. The facility register.
  data/clean/bia_tribal_leaders_directory.csv              587
      one row per directory ENTRY (a nation can hold several), structured -
      Cedar's `bia_directory` source reads this as HTML today.
  data/clean/bia_aian_national_lar.csv                     335
      one row per Land Area Record: the external extent of federal Indian
      reservations and associated trust / restricted-fee / mixed-ownership
      land, with GISACRES.
  data/clean/bia_ofa_petitioners.csv                        20
      one row per Office of Federal Acknowledgment petitioner. This is the
      NEGATIVE CASE `docs/ASSERTION_LAYER.md` records as absent:
      "entity.is_federally_recognized has no negative case". A roster with
      only positives cannot support any claim about the boundary.

WHAT IS DELIBERATELY NOT TAKEN
------------------------------
Geometry. `returnGeometry=false` on every request: the 335 LAR polygons are
large, Cedar has no spatial consumer, and `GISACRES` is an attribute. Lat/long
columns that the publisher stores as ATTRIBUTES are kept, because they are
attributes.

PERSONAL DATA
-------------
`Tribal_Leaders_Directory_new` and `PL102_477_Contracts` carry named
individuals in their public role (a tribal chair, a BIA awarding officer's
technical representative). Those rows are harvested - they are the
publisher's own public directory - but the columns are stamped
`publishable = N` in the codebook fragment, per PUBLICATION_POLICY's standing
rule that a natural person's contact details are held and not shipped. The
`email`, `phone`, `fax` and personal-name columns are written to
`data/clean` and marked; the ship chain reads the mark.

RE-RUNNING
----------
`pull` is idempotent and skips a layer whose raw JSON is already on disk with
a matching row count unless `--refetch` is passed. `build` reads only local
files and makes zero network calls. Every raw page carries its sha256 in
`data/raw/external/biamaps/_manifest.json`; a `?wpdmdl=` harvester once
reported 302 distinct documents that were the same PDF 302 times, and page
hashing is what catches that.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

_spec = importlib.util.spec_from_file_location("cedar_arcgis", HERE / "cedar_arcgis.py")
ag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ag)                                       # type: ignore

SCRIPT = "1119_acquire_biamaps_arcgis"
HOST = "biamaps.geoplatform.gov"
BASE = f"https://{HOST}/server/rest/services"
RAW = ROOT / "data" / "raw" / "external" / "biamaps"
CLEAN = ROOT / "data" / "clean"
LOG = ROOT / "logs" / f"{SCRIPT}.jsonl"
MANIFEST = RAW / "_manifest.json"

PAGE_SIZE = 2000          # the service's own maxRecordCount; do not exceed it
PAUSE_S = 1.5

# service path -> (output table stem, the count the survey measured)
LAYERS: list[dict] = [
    {"svc": "Hosted/BIA_Mineral_Acreage_Table",
     "stem": "resource_bia_mineral_acreage_tracts",
     "survey_count": 249165,
     "grain": "one row per (tract, resource, ownership type) as LTRO holds it"},
    {"svc": "Hosted/Tribal_Leaders_Directory_new",
     "stem": "bia_tribal_leaders_directory",
     "survey_count": 587,
     "grain": "one row per tribal-leaders directory entry"},
    {"svc": "DivLTR/BIA_AIAN_National_LAR",
     "stem": "bia_aian_national_lar",
     "survey_count": 335,
     "grain": "one row per BIA Land Area Record"},
    {"svc": "BOGS/BIA_Office",
     "stem": "bia_offices",
     "survey_count": 93,
     "grain": "one row per BIA office"},
    {"svc": "Hosted/PL102_477_Contracts",
     "stem": "bia_pl102_477_plans",
     "survey_count": 84,
     "grain": "one row per PL 102-477 plan agreement"},
    {"svc": "Hosted/OFAPetitioners",
     "stem": "bia_ofa_petitioners",
     "survey_count": 20,
     "grain": "one row per Office of Federal Acknowledgment petitioner"},
]

# Columns that are a natural person's contact details. Harvested (the
# publisher publishes them), held, never shipped.
NOT_PUBLISHABLE = {
    "email", "email_bia_aotr", "phone", "fax", "pocemailaddress",
    "contactname", "pocfirstname", "poclastname", "pocmiddlename",
    "pocprefix", "pocsuffix", "firstname", "lastname", "middlename",
    "salutation", "suffix", "aka", "physicaladdress", "mailingaddress",
}

# ArcGIS epoch-millisecond date fields, per layer. Rendered to ISO alongside
# the raw integer - the integer is the evidence, the ISO is the convenience.
DATE_FIELDS = {"plan_start_date", "plan_expiration_date", "plan_renewal_date",
               "inactivated_date", "dateelected", "nextelection"}


def layer_url(svc: str) -> str:
    return f"{BASE}/{svc}/FeatureServer/0"


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"host": HOST, "script": SCRIPT, "layers": {}}


def _save_manifest(m: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    m["written_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------

def cmd_probe() -> int:
    """Counts and robots posture only. No bulk. Cheap enough to run any time."""
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S)
    posture = ag.robots_posture(f"https://{HOST}/server/rest/services")
    print(f"robots.txt  status={posture['robots_status']}  "
          f"served={posture['robots_served']}  verdict={posture['verdict']}")
    print(f"  (our own UA alone would have said: {posture['naive_our_ua_verdict']})")
    if posture["verdict"] != "ALLOWED":
        print("REFUSED by robots for at least one agent token we plausibly are.")
        return 1
    total = 0
    for L in LAYERS:
        u = layer_url(L["svc"])
        n = ag.arcgis_count(sess, u)
        meta = ag.arcgis_layer_meta(sess, u)
        total += n
        flag = "" if n == L["survey_count"] else f"  !! survey said {L['survey_count']:,}"
        print(f"{n:>9,}  {L['svc']:<42} maxRecordCount={meta.get('maxRecordCount')}{flag}")
    print(f"{total:>9,}  TOTAL across {len(LAYERS)} layers "
          f"({sess.n_requests} requests, {sess.bytes_read:,} bytes)")
    return 0


def cmd_pull(refetch: bool = False) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    posture = ag.require_allowed(f"https://{HOST}/server/rest/services")
    lock = ag.claim_host(HOST, SCRIPT, queue=[L["svc"] for L in LAYERS])
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S, deadline_s=3 * 3600)
    man = _load_manifest()
    man["robots"] = posture
    downloaded, skipped, refused = 0, 0, []
    try:
        for L in LAYERS:
            out = RAW / f"{L['stem']}.json"
            u = layer_url(L["svc"])
            advertised = ag.arcgis_count(sess, u)
            prior = man["layers"].get(L["stem"], {})
            if out.exists() and not refetch and prior.get("rows") == advertised:
                print(f"SKIP  {L['stem']:<40} {advertised:>9,} already on disk, "
                      "count unchanged")
                skipped += 1
                continue
            meta = ag.arcgis_layer_meta(sess, u)
            oid = meta.get("objectIdField") or "objectid"
            page_cap = min(PAGE_SIZE, int(meta.get("maxRecordCount") or PAGE_SIZE))

            def _tick(pages, n, _adv=advertised, _stem=L["stem"]):
                if pages % 20 == 0 or n >= _adv:
                    print(f"      {_stem}: {n:,}/{_adv:,} in {pages} pages", flush=True)

            feats, shas = ag.arcgis_page_all(sess, u, oid, page_cap, on_page=_tick)
            # RECONCILE against a FRESH returnCountOnly taken AFTER the last
            # page, not against the one taken before. That is the check the
            # FERC truncation incident earned.
            after = ag.arcgis_count(sess, u)
            ag.reconcile(len(feats), after, L["stem"])
            payload = {
                "source_url": u,
                "service_path": L["svc"],
                "objectIdField": oid,
                "fields": meta.get("fields", []),
                "count_before_paging": advertised,
                "count_after_paging": after,
                "rows": len(feats),
                "page_sha256": shas,
                "distinct_page_sha256": len(set(shas)),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "features": feats,
            }
            tmp = out.with_suffix(".json.part")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(out)                       # .part then rename: an
                                                   # interruption must not look
                                                   # like a completion
            man["layers"][L["stem"]] = {
                "service_path": L["svc"], "source_url": u,
                "rows": len(feats), "advertised_after": after,
                "pages": len(shas), "distinct_page_sha256": len(set(shas)),
                "page_sha256": shas,
                "retrieved_at": payload["retrieved_at"],
                "file": str(out.relative_to(ROOT)).replace("\\", "/"),
            }
            _save_manifest(man)
            downloaded += 1
            print(f"PULL  {L['stem']:<40} {len(feats):>9,} rows, {len(shas)} pages, "
                  f"{len(set(shas))} distinct page hashes  RECONCILED")
    except ag.EdgeBlocked as e:
        refused.append(str(e))
        print(f"EDGE BLOCK - stopping the run.\n  {e}")
        return 2
    finally:
        _save_manifest(man)
        ag.release_host(lock, downloaded_this_run=downloaded,
                        already_on_disk_skipped=skipped,
                        refused_by_host=refused,
                        requests_made=sess.n_requests,
                        bytes_read=sess.bytes_read)
    print(f"\n{downloaded} layers pulled, {skipped} skipped, "
          f"{sess.n_requests} requests, {sess.bytes_read:,} bytes.")
    return 0


def _iso_from_epoch_ms(v):
    if v in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).date().isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def cmd_build() -> int:
    """Raw JSON -> data/clean CSV. ZERO network calls."""
    CLEAN.mkdir(parents=True, exist_ok=True)
    man = _load_manifest()
    if not man.get("layers"):
        print("nothing pulled yet - run `pull` first")
        return 1
    summary = []
    for L in LAYERS:
        src = RAW / f"{L['stem']}.json"
        if not src.exists():
            print(f"MISSING raw {src.name} - skipped (state: NOT_ACQUIRED)")
            continue
        d = json.loads(src.read_text(encoding="utf-8"))
        feats = d["features"]
        cols = [f["name"] for f in d["fields"]]
        date_cols = [c for c in cols if c.lower() in DATE_FIELDS]
        header = (cols
                  + [c + "_iso" for c in date_cols]
                  + ["source_url", "source_service_path", "retrieved_at",
                     "source_id", "population_basis"])
        out = CLEAN / f"{L['stem']}.csv"
        tmp = out.with_suffix(".csv.part")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for ft in feats:
                a = ft.get("attributes", {})
                row = [a.get(c, "") if a.get(c) is not None else "" for c in cols]
                row += [_iso_from_epoch_ms(a.get(c)) for c in date_cols]
                row += [d["source_url"], d["service_path"], d["retrieved_at"],
                        "bia_biamaps_arcgis", "TYPE_FILTER"]
                w.writerow(row)
        tmp.replace(out)
        # Re-read what was written, and reconcile against the manifest. A
        # writer that reports its own intent is not a measurement.
        with out.open("r", encoding="utf-8", newline="") as fh:
            n = sum(1 for _ in csv.reader(fh)) - 1
        adv = man["layers"][L["stem"]]["advertised_after"]
        ag.reconcile(n, adv, f"{L['stem']} (built CSV vs source count)")
        nonpub = sorted(c for c in cols if c.lower() in NOT_PUBLISHABLE)
        summary.append({"table": out.name, "rows": n, "columns": len(header),
                        "grain": L["grain"], "held_not_published": nonpub})
        print(f"BUILD {out.name:<46} {n:>9,} rows x {len(header)} cols"
              + (f"   [{len(nonpub)} held-not-published cols]" if nonpub else ""))
    (ROOT / "docs" / "biamaps_acquisition_1119.json").write_text(
        json.dumps({"script": SCRIPT, "host": HOST,
                    "built_at": datetime.now(timezone.utc).isoformat(),
                    "tables": summary}, indent=2), encoding="utf-8")
    print(f"\n{len(summary)} tables built, "
          f"{sum(s['rows'] for s in summary):,} rows total.")
    return 0


def cmd_verify() -> int:
    """Exit 1 on breach. Runs against the LIVE files, not against intent."""
    man = _load_manifest()
    fails, checks = [], 0

    def ck(name, cond, detail=""):
        nonlocal checks
        checks += 1
        print(("OK  " if cond else "FAIL") + "  " + name + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    if not man.get("layers"):
        print("UNMEASURED - nothing pulled. An absence of evidence is not "
              "evidence of absence; run `pull`.")
        return 1

    for L in LAYERS:
        stem = L["stem"]
        rec = man["layers"].get(stem)
        if not rec:
            ck(f"{stem}: manifest entry present", False)
            continue
        ck(f"{stem}: rows == source returnCountOnly",
           rec["rows"] == rec["advertised_after"],
           f"{rec['rows']:,} vs {rec['advertised_after']:,}")
        ck(f"{stem}: rows == the count the 2026-09-02 survey measured",
           rec["rows"] == L["survey_count"],
           f"{rec['rows']:,} vs {L['survey_count']:,}")
        ck(f"{stem}: every page hash distinct (no repeated body)",
           rec["distinct_page_sha256"] == rec["pages"],
           f"{rec['distinct_page_sha256']}/{rec['pages']}")
        p = CLEAN / f"{stem}.csv"
        if not p.exists():
            ck(f"{stem}: clean table exists", False, str(p))
            continue
        with p.open("r", encoding="utf-8", newline="") as fh:
            rdr = csv.reader(fh)
            hdr = next(rdr)
            n = sum(1 for _ in rdr)
        ck(f"{stem}: clean CSV row count == source count", n == rec["advertised_after"],
           f"{n:,} vs {rec['advertised_after']:,}")
        ck(f"{stem}: provenance columns present",
           {"source_url", "retrieved_at", "source_id"} <= set(hdr))
        ck(f"{stem}: no .part left behind", not (CLEAN / f"{stem}.csv.part").exists())

    total = sum(r["rows"] for r in man["layers"].values())
    ck(f"total across {len(man['layers'])} layers is 250,284",
       total == 250_284, f"{total:,}")

    print(f"\n{checks} checks, {len(fails)} failed.")
    if fails:
        print("BREACH: " + "; ".join(fails))
        return 1
    return 0


def cmd_selftest() -> int:
    """Prove `verify` FIRES. Injects a violation into a COPY of the manifest."""
    import copy
    man = _load_manifest()
    if not man.get("layers"):
        print("UNMEASURED - selftest needs a pulled manifest to corrupt.")
        return 1
    backup = copy.deepcopy(man)
    try:
        stem = next(iter(man["layers"]))
        man["layers"][stem]["rows"] = man["layers"][stem]["advertised_after"] - 1
        _save_manifest(man)
        print("--- verify against an INJECTED short-retrieval -------------")
        rc = cmd_verify()
        if rc != 1:
            print("SELFTEST FAIL: verify did not exit 1 on an injected violation")
            return 1
        print("--- restoring and re-verifying -----------------------------")
    finally:
        _save_manifest(backup)
    rc = cmd_verify()
    print("\nSELFTEST " + ("PASS" if rc == 0 else "FAIL (clean state does not verify)"))
    return 0 if rc == 0 else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "probe":
        return cmd_probe()
    if cmd == "pull":
        return cmd_pull("--refetch" in sys.argv)
    if cmd == "build":
        return cmd_build()
    if cmd == "verify":
        return cmd_verify()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
