#!/usr/bin/env python3
"""
215_pull_nm_revenue_sharing_quarters.py -- Cedar Press.

Drains the folder `code/214_...py` found:

    "Revenue Sharing News Release by Quarter"
    folderId c4cd69d1-1b8b-4d30-8db6-15383445f5bb
    -> 25 year sub-folders, 2002 through 2026

Cedar already holds 2002-2022 (84 PDFs, 1,072 rows in
`data/clean/gaming_capacity_official.csv`). **2023, 2024, 2025 and 2026 were
recorded as unrecoverable** and are four folder GUIDs the prior pass never had:

    2023 d39e2ffb-5db6-42c7-a112-9e271c29ef08
    2024 14238098-17d5-4c1f-a812-8afbdc848a29
    2025 e20c75cf-7472-411f-a49f-8b25456e1c78
    2026 b008f63c-efda-459f-a86d-a89b858ac3c0

Also pulls the NMGCB monthly **Quick Facts** tree, which is a second, denser
series for the same money and was not in Cedar at all.

Every year folder is re-enumerated, including ones already held, so the run can
report `already_on_disk_skipped` honestly rather than inferring it.

WRITES
  data/raw/external/gaming_official/nm_tribal_revenue_sharing/*.pdf
  data/raw/external/gaming_official/bypass_2026-08-26/nm_quick_facts/*.pdf
  data/raw/external/gaming_official/bypass_2026-08-26/_nm_quarters_state.json
"""
import json, re, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
GO = CEDAR / "data" / "raw" / "external" / "gaming_official"
BYPASS = GO / "bypass_2026-08-26"
PDFDIR = GO / "nm_tribal_revenue_sharing"
QFDIR = BYPASS / "nm_quick_facts"

ACC = "c5d7c9d5c4424c1fb796bb563e87e31c"
API = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/GetWidgetFiles"
FILEBASE = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/PublicFiles"
REVSHARE_ROOT = ("c4cd69d1-1b8b-4d30-8db6-15383445f5bb",
                 "14c4ce0c-4add-49ac-99cd-1d7470c8ff12")

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
      "Referer": "https://www.gcb.nm.gov/",
      "Accept": "application/json, text/javascript, */*;q=0.8"}

MIN_GAP = 1.5
RUN_DEADLINE = time.time() + 90 * 60
_last = [0.0]


def gap():
    d = MIN_GAP - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def fetch(url, tries=3, binary=False):
    delay, last = 15, None
    for i in range(tries):
        if time.time() > RUN_DEADLINE:
            return "DEADLINE", None
        gap()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                b = r.read()
            return r.status, (b if binary else b.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, None
            last = e.code
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        if i < tries - 1:
            time.sleep(delay)
            delay *= 2
    return last, None


def listing(folder, widget, root=None):
    q = urllib.parse.urlencode({"widgetId": widget, "folderId": folder,
                                "rootFolderId": root or folder, "accountGUID": ACC})
    st, body = fetch(API + "?" + q)
    if st != 200 or not body:
        return st, {}
    try:
        return st, (json.loads(body).get("data") or {})
    except Exception as e:
        return f"unparseable: {e}", {}


def download(fileid, name, outdir, prefix):
    outdir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    out = outdir / f"{prefix}{safe}"
    if out.exists():
        return "already_on_disk_skipped", out.name
    url = f"{FILEBASE}/{ACC}/{fileid}/{urllib.parse.quote(name)}"
    st, body = fetch(url, binary=True)
    if st == 200 and body and body[:4] == b"%PDF":
        tmp = out.with_suffix(out.suffix + ".part")
        tmp.write_bytes(body)
        tmp.rename(out)
        return "downloaded", out.name
    return f"refused_{st}", url


def main():
    state = {"started": datetime.now(timezone.utc).isoformat(),
             "revenue_sharing_years": {}, "quick_facts_years": {},
             "downloaded": [], "already_on_disk_skipped": [], "refused_by_host": []}

    st, root = listing(*REVSHARE_ROOT)
    years = root.get("folders") or []
    print("revenue-sharing year folders:", len(years), flush=True)
    for y in sorted(years, key=lambda f: f.get("name", "")):
        # THE PARAMETER RULE, measured 2026-08-26 on the 2023 folder:
        # `rootFolderId` MUST MATCH THE WIDGET. Pairing the year's own
        # `widgetId` with the PARENT as `rootFolderId` returns HTTP 200 and
        # `files: []` -- a silent empty, not an error. Both consistent pairings
        # work and return the same four files:
        #   widgetId=<year widget>, rootFolderId=<year folder>      <- used here
        #   widgetId=<root widget>, rootFolderId=<root folder>
        st2, d2 = listing(y["folderId"], y.get("widgetId") or REVSHARE_ROOT[1],
                          root=y["folderId"])
        files = d2.get("files") or []
        rec = {"status": st2, "folder_id": y["folderId"], "n_files": len(files),
               "files": []}
        for f in files:
            verdict, what = download(f["fileId"], f["name"], PDFDIR,
                                     f"nmgcb_revshare_{y['name']}_")
            rec["files"].append({"name": f["name"], "fileId": f["fileId"],
                                 "verdict": verdict, "as": what})
            if verdict == "downloaded":
                state["downloaded"].append(f"{y['name']}/{f['name']}")
            elif verdict == "already_on_disk_skipped":
                state["already_on_disk_skipped"].append(f"{y['name']}/{f['name']}")
            else:
                state["refused_by_host"].append({"year": y["name"], "file": f["name"],
                                                 "verdict": verdict})
        state["revenue_sharing_years"][y["name"]] = rec
        print(f"  {y['name']}: {len(files)} files", flush=True)
        if time.time() > RUN_DEADLINE:
            state["stopped"] = "RUN_DEADLINE"
            break

    # Quick Facts: monthly, a denser second series for the same money.
    qf_roots = json.loads((BYPASS / "_nm_recovery_state.json").read_text(encoding="utf-8"))
    for fid, meta in qf_roots.get("folders", {}).items():
        nm = (meta.get("name") or "")
        if not re.match(r"^FY ?\d{4}$", nm):
            continue
        for f in [{"name": n} for n in (meta.get("file_names") or [])]:
            pass  # names only; ids come from the listing file
        lst = BYPASS / f"nm_folder_listing_{fid}.json"
        if not lst.exists():
            continue
        files = ((json.loads(lst.read_text(encoding="utf-8")).get("data") or {})
                 .get("files") or [])
        rec = {"n_files": len(files), "files": []}
        for f in files:
            verdict, what = download(f["fileId"], f["name"], QFDIR,
                                     f"nmgcb_quickfacts_{nm.replace(' ', '')}_")
            rec["files"].append({"name": f["name"], "verdict": verdict, "as": what})
            if verdict == "downloaded":
                state["downloaded"].append(f"QF {nm}/{f['name']}")
            elif verdict == "already_on_disk_skipped":
                state["already_on_disk_skipped"].append(f"QF {nm}/{f['name']}")
            else:
                state["refused_by_host"].append({"qf_year": nm, "file": f["name"],
                                                 "verdict": verdict})
        state["quick_facts_years"][nm] = rec
        print(f"  QuickFacts {nm}: {len(files)} files", flush=True)

    state["finished"] = datetime.now(timezone.utc).isoformat()
    state["n_downloaded"] = len(state["downloaded"])
    state["n_skipped"] = len(state["already_on_disk_skipped"])
    state["n_refused"] = len(state["refused_by_host"])
    (BYPASS / "_nm_quarters_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({k: state[k] for k in
                      ("n_downloaded", "n_skipped", "n_refused")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
