"""220 — Do the 6,217 no-BMF Schedule I recipient EINs exist in the IRS e-file corpus?

`docs/SCHEDULE_I_BUILD_LOG.md` line 133 records:

    "6,217 distinct recipient EINs are printed on a filed Schedule I and absent
     from the entire BMF. *That* is the 7871 signature — an entity outside the
     Form 990 universe, most often a tribal government. It files no return.
     **This is not a gap and is not queued as one.**"

That conclusion was reached from ONE source (the BMF, 1,957,340 rows). The BMF
is the roster of organisations with an exemption ruling on file. An entity can
be absent from it for at least four reasons that are not "it is a tribal
government":

  * it is a STATE or LOCAL GOVERNMENT unit (no exemption ruling; not in the BMF)
  * it is a FOR-PROFIT company (a Schedule I recipient can be one)
  * it is a component of a parent that files under a different EIN
  * its exemption was revoked / it merged / it terminated before the BMF vintage

This script does not argue. It measures, against a SECOND corpus that has a
different membership rule: the IRS Form 990 e-file index, which lists every
electronically filed return by EIN, 2011 onward. If a no-BMF EIN appears there,
"it files no return" is false FOR THAT EIN.

It also decomposes the $4.92B by the FILER, because the headline is quoted as if
it were a Native-philanthropy fact.

STAGES
  profile   local only, zero network. Decompose the 6,217 / $4.92B.
  index     stream the IRS e-file index CSVs (apps.irs.gov), filter to our EINs.
  report    join and write the staged result.

WHAT IT REFUSES
  * It writes NOTHING into any shared table. Output is staged under
    review/ and data/raw/external/untapped_2026-08-26/.
  * It honours logs/_HOSTLOCK_apps.irs.gov.json and claims/releases it.
  * It streams the index and never stores a whole year's CSV.

py -3 code/220_test_nobmf_eins_against_efile_index.py profile
py -3 code/220_test_nobmf_eins_against_efile_index.py index
py -3 code/220_test_nobmf_eins_against_efile_index.py report
"""
import csv, io, json, os, sys, time, urllib.request, collections, datetime, pathlib

csv.field_size_limit(10 ** 8)
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHED_I = ROOT / "data" / "clean" / "np_schedule_i_grants.csv"
OUT = ROOT / "data" / "raw" / "external" / "untapped_2026-08-26"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)

SCRIPT = "220_test_nobmf_eins_against_efile_index.py"
HOST = "apps.irs.gov"
INDEX_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{y}/index_{y}.csv"
# MEASURED 2026-08-26: apps.irs.gov serves index_2017..index_2026.
#   index_2016.csv and earlier answer HTTP 302 -> https://www.irs.gov/404.
#   A 302 to a 404 page is not a 404 about the object; record it as a redirect.
# Coverage caveat that travels with every verdict this script writes:
#   mandatory e-filing arrived with the Taxpayer First Act and the e-file index
#   begins at SUBMISSION YEAR 2017.  Absence from it means "did not e-file a
#   990-family return 2017-2026".  It does NOT mean "files no return".
YEARS = [int(y) for y in os.environ.get(
    "IDX_YEARS", "2017,2018,2019,2020,2021,2022,2023,2024,2025,2026").split(",")]
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
GAP = 1.5
DEADLINE_S = 100 * 60
START = time.time()


def log(m):
    print(m, flush=True)


# --------------------------------------------------------------- host lock
def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            log(f"HOSTLOCK held by {cur.get('script')}; appending and exiting")
            cur.setdefault("queue", []).append({"script": f"code/{SCRIPT}", "note": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            return False
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{SCRIPT}",
        "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active": True, "queue": [], "note": note,
        "policy": "sequential, single stream, >=1.5s gap, no retry loop",
    }, indent=1), encoding="utf-8")
    return True


def release_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"host": HOST}
    cur.update(active=False, released=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               note=note)
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


# --------------------------------------------------------------- profile
def load_nobmf():
    """Return {ein: dict(total, rows, name, state, native_filer_usd, filers)}."""
    d = {}
    for row in csv.DictReader(SCHED_I.open(encoding="utf-8-sig")):
        if row["recipient_bmf_status"] != "absent_from_full_irs_bmf":
            continue
        ein = (row["recipient_ein"] or "").strip()
        if not ein:
            continue
        try:
            v = float(row["cash_grant_usd"] or 0)
        except ValueError:
            v = 0.0
        r = d.setdefault(ein, dict(ein=ein, total_usd=0.0, rows=0,
                                   name=row["recipient_name_as_filed"],
                                   state=row["recipient_state"],
                                   native_filer_usd=0.0, native_filer_rows=0,
                                   filers=set()))
        r["total_usd"] += v
        r["rows"] += 1
        r["filers"].add(row["filer_name_as_filed"])
        if row["filer_is_ruled_native"] == "1":
            r["native_filer_usd"] += v
            r["native_filer_rows"] += 1
    return d


def step_profile():
    d = load_nobmf()
    tot = sum(r["total_usd"] for r in d.values())
    nat = sum(r["native_filer_usd"] for r in d.values())
    log(f"distinct no-BMF recipient EINs : {len(d):,}")
    log(f"cash grants to them            : ${tot:,.0f}")
    log(f"...from filers ruled Native    : ${nat:,.0f} "
        f"({100*nat/tot:.3f}%) on "
        f"{sum(r['native_filer_rows'] for r in d.values()):,} rows")

    # decomposition by filer
    byfiler = collections.defaultdict(float)
    for row in csv.DictReader(SCHED_I.open(encoding="utf-8-sig")):
        if row["recipient_bmf_status"] != "absent_from_full_irs_bmf":
            continue
        try:
            v = float(row["cash_grant_usd"] or 0)
        except ValueError:
            v = 0.0
        byfiler[(row["filer_ein"], row["filer_is_ruled_native"])] += v
    top = sorted(byfiler.items(), key=lambda x: -x[1])[:20]

    with (REVIEW / "schedule_i_nobmf_recipient_eins_2026-08-26.csv.part").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipient_ein", "recipient_name_as_filed", "recipient_state",
                    "cash_grant_usd", "schedule_i_rows",
                    "usd_from_native_ruled_filers", "n_distinct_filers",
                    "top_filer"])
        for r in sorted(d.values(), key=lambda x: -x["total_usd"]):
            w.writerow([r["ein"], r["name"], r["state"], f"{r['total_usd']:.2f}",
                        r["rows"], f"{r['native_filer_usd']:.2f}",
                        len(r["filers"]), sorted(r["filers"])[0]])
    os.replace(REVIEW / "schedule_i_nobmf_recipient_eins_2026-08-26.csv.part",
               REVIEW / "schedule_i_nobmf_recipient_eins_2026-08-26.csv")

    (OUT / "_220_profile.json").write_text(json.dumps({
        "distinct_nobmf_recipient_eins": len(d),
        "cash_grant_usd": tot,
        "cash_grant_usd_from_native_ruled_filers": nat,
        "top_filers": [{"filer_ein": k[0], "filer_is_ruled_native": k[1],
                        "usd": v} for k, v in top],
    }, indent=1), encoding="utf-8")
    log("wrote review/schedule_i_nobmf_recipient_eins_2026-08-26.csv")
    for k, v in top[:10]:
        log(f"  ${v:>15,.0f}  filer_ein={k[0]}  native={k[1]}")


# --------------------------------------------------------------- index
def step_index():
    d = load_nobmf()
    want = set(d)
    log(f"testing {len(want):,} EINs against the IRS e-file index")
    if not claim_host("no-BMF Schedule I recipient EIN membership test"):
        return 3
    hits_path = OUT / "_220_efile_hits.csv"
    have_years = set()
    rows_out = []
    if hits_path.exists():
        for r in csv.DictReader(hits_path.open(encoding="utf-8-sig")):
            rows_out.append(r)
            have_years.add(int(r["index_year"]))
    state = {"downloaded_this_run": [], "already_on_disk_skipped": [],
             "refused_by_host": [], "accepted_then_failed_server_side": []}
    try:
        for y in YEARS:
            if y in have_years:
                state["already_on_disk_skipped"].append(y)
                log(f"  {y}: cached")
                continue
            if time.time() - START > DEADLINE_S:
                log("RUN_DEADLINE reached; stopping")
                break
            url = INDEX_URL.format(y=y)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            try:
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=180) as resp:
                    if resp.status != 200:
                        state["refused_by_host"].append([y, resp.status])
                        log(f"  {y}: HTTP {resp.status}")
                        continue
                    n = kept = 0
                    buf = io.TextIOWrapper(resp, encoding="utf-8", errors="replace")
                    rdr = csv.DictReader(buf)
                    for rec in rdr:
                        n += 1
                        ein = (rec.get("EIN") or rec.get("ein") or "").strip().zfill(9)
                        if ein in want:
                            kept += 1
                            rows_out.append({
                                "index_year": y, "ein": ein,
                                "taxpayer_name": rec.get("TAXPAYER_NAME") or rec.get("taxpayer_name") or "",
                                "return_type": rec.get("RETURN_TYPE") or rec.get("return_type") or "",
                                "tax_period": rec.get("TAX_PERIOD") or rec.get("tax_period") or "",
                                "object_id": rec.get("OBJECT_ID") or rec.get("object_id") or "",
                                "index_url": url,
                            })
                state["downloaded_this_run"].append(y)
                log(f"  {y}: {n:,} index rows -> {kept} of ours  ({time.time()-t0:.0f}s)")
            except Exception as e:
                state["refused_by_host"].append([y, str(e)[:200]])
                log(f"  {y}: FAILED {e}")
                if not state["downloaded_this_run"]:
                    log("first object refused and nothing has landed -> the HOST is refusing")
                    break
            time.sleep(GAP)
    finally:
        release_host("no-BMF EIN membership test complete")

    tmp = str(hits_path) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["index_year", "ein", "taxpayer_name",
                                          "return_type", "tax_period",
                                          "object_id", "index_url"])
        w.writeheader()
        w.writerows(rows_out)
    os.replace(tmp, hits_path)
    (OUT / "_220_index_state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    log(f"wrote {hits_path} ({len(rows_out):,} rows)")
    return 0


# --------------------------------------------------------------- report
def step_report():
    d = load_nobmf()
    hits_path = OUT / "_220_efile_hits.csv"
    hit_ein = collections.defaultdict(list)
    if hits_path.exists():
        for r in csv.DictReader(hits_path.open(encoding="utf-8-sig")):
            hit_ein[r["ein"]].append(r)
    tot = sum(r["total_usd"] for r in d.values())
    hit_usd = sum(d[e]["total_usd"] for e in hit_ein if e in d)
    log(f"no-BMF EINs                     : {len(d):,}   ${tot:,.0f}")
    log(f"...FOUND in the IRS e-file index: {len(hit_ein):,}   ${hit_usd:,.0f} "
        f"({100*len(hit_ein)/max(1,len(d)):.1f}% of EINs, "
        f"{100*hit_usd/max(1.0,tot):.1f}% of dollars)")
    log(f"...still absent from both       : {len(d)-len(hit_ein):,}   "
        f"${tot-hit_usd:,.0f}")
    out = REVIEW / "schedule_i_nobmf_eins_efile_verdict_2026-08-26.csv"
    tmp = str(out) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipient_ein", "recipient_name_as_filed", "recipient_state",
                    "cash_grant_usd", "usd_from_native_ruled_filers",
                    "efile_index_years", "efile_return_types",
                    "efile_taxpayer_name", "verdict"])
        for r in sorted(d.values(), key=lambda x: -x["total_usd"]):
            h = hit_ein.get(r["ein"], [])
            w.writerow([r["ein"], r["name"], r["state"], f"{r['total_usd']:.2f}",
                        f"{r['native_filer_usd']:.2f}",
                        "|".join(sorted({x["index_year"] for x in h})),
                        "|".join(sorted({x["return_type"] for x in h})),
                        (h[0]["taxpayer_name"] if h else ""),
                        "FILES_A_990_EFILE" if h else "ABSENT_FROM_BMF_AND_EFILE"])
    os.replace(tmp, out)
    log(f"wrote {out}")
    (OUT / "_220_verdict.json").write_text(json.dumps({
        "nobmf_eins": len(d), "nobmf_usd": tot,
        "found_in_efile_index": len(hit_ein), "found_usd": hit_usd,
        "index_years_swept": sorted({int(x["index_year"]) for v in hit_ein.values() for x in v}),
    }, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "profile"
    sys.exit({"profile": lambda: (step_profile(), 0)[1],
              "index": step_index,
              "report": step_report}[stage]())
