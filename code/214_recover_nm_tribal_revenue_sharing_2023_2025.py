#!/usr/bin/env python3
"""
214_recover_nm_tribal_revenue_sharing_2023_2025.py -- Cedar Press.

RECOVERS the New Mexico per-tribe quarterly Adjusted Net Win series past the
2022 Q4 wall that `docs/GAMING_CAPACITY_OFFICIAL_LOG.md` recorded as closed.

THREE FACTS THE PRIOR PASS DID NOT HAVE, EACH OF WHICH ALONE UNBLOCKS IT
------------------------------------------------------------------------

**1. `nmgcb.org` IS NOT THE NEW MEXICO GAMING CONTROL BOARD ANY MORE.**
Measured 2026-08-26. `https://www.nmgcb.org/` returns 403 at the root -- which
is what was recorded -- but ANY OTHER PATH returns a 24 KB page, and that page
reads:

    <title>Page not found -</title>
    "Mejores Casinos Online / Sobre nosotros / Contacto
     ... Contacto - (c) 2025 nmgcb.org"

The domain lapsed and was re-registered as a Spanish-language online-casino
affiliate site. **The 403 was never Cloudflare protecting a regulator; there is
no regulator behind it.** Anything scraped from that host today would be an
advertising site wearing the regulator's old name -- a worse outcome than the
block. The agency is at **`www.gcb.nm.gov`**, which answers HTTP 200 to a plain
browser User-Agent, and whose `robots.txt` is `User-agent: * / Disallow:` --
i.e. everything allowed.

**2. THE FOLDER IDS FOR 2023-2025 ARE ON THE LIVE PAGE.**
`https://www.gcb.nm.gov/new-mexico-gaming-control-board-office-of-the-state-gaming-representative/`
carries five `data-folder-id` GUIDs, none of them in
`nm_revsharing_folders.txt`. The prior note "getting past Cloudflare once, to
read the current page's GUIDs, is the only route" had the mechanism exactly
right and the host wrong.

**3. THE WIDGET API HOST IN THE PRIOR PROBE WAS WRONG, WHICH IS WHY IT 502'd.**
Four spellings of `api.realfile.rtsclients.com/GetWidgetFiles` were tried and
all returned 502 or 404. That host serves `PublicFiles/...` and nothing else.
The real API is an AWS API Gateway, and it is named in the site's own
JavaScript -- `https://prod.realfile.rtsclients.com/js/rf-tables.js` and
`https://cdn.rtsclients.com/SDKs/RealFile/JavaScript/rf_sdk.min.js`:

    var realFileLambdaURL = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/";
    RFModule.getWidgetFiles = ... url: realFileLambdaURL + "GetWidgetFiles" ... type: "GET"
    widgets.push({ widgetId, folderId, rootFolderId, accountGUID })

**READ THE CLIENT, DO NOT GUESS THE SERVER.** Four guessed spellings cost four
requests and produced one wrong conclusion; reading the SDK cost one request
and produced the call signature, the parameter names and the HTTP verb.

The call is validated against the 2022 folder already on disk BEFORE any new
folder is touched -- the returned `fileId`s must equal the ones in
`nm_revsharing_files.json`. A control that reproduces known data is what makes
a new answer from the same endpoint trustworthy.

WRITES
  data/raw/external/gaming_official/bypass_2026-08-26/nm_folder_listing_<guid>.json
  data/raw/external/gaming_official/nm_tribal_revenue_sharing/<file>.pdf   (new only)
  data/raw/external/gaming_official/bypass_2026-08-26/_nm_recovery_state.json
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
GO = CEDAR / "data" / "raw" / "external" / "gaming_official"
BYPASS = GO / "bypass_2026-08-26"
PDFDIR = GO / "nm_tribal_revenue_sharing"
LOCK_API = CEDAR / "logs" / "_HOSTLOCK_klvg4oyd4j.execute-api.us-west-2.amazonaws.com.json"

ACC = "c5d7c9d5c4424c1fb796bb563e87e31c"
API = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/GetWidgetFiles"
FILEBASE = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/PublicFiles"
PAGE = ("https://www.gcb.nm.gov/"
        "new-mexico-gaming-control-board-office-of-the-state-gaming-representative/")
QUICKFACTS = ("https://www.gcb.nm.gov/"
              "new-mexico-gaming-control-board-quick-facts-and-archives/")

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
      "Referer": "https://www.gcb.nm.gov/",
      "Accept": "application/json, text/javascript, text/html;q=0.9, */*;q=0.8"}

MIN_GAP = 2.0
RUN_DEADLINE = time.time() + 90 * 60
_last = [0.0]


def gap():
    d = MIN_GAP - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def fetch(url, tries=3, binary=False):
    delay = 20
    last = None
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


def widget_files(folder, widget, root=None):
    # MEASURED: a SUB-folder returns `files: []` when `rootFolderId` is set to
    # the sub-folder itself. `rf-tables.js` `treeviewNavigate()` sends
    # rootFolderId = the WIDGET's own folder and folderId = the clicked one, and
    # only that pairing returns contents. Every FY2023-FY2026 folder read as
    # empty until this was fixed -- an empty result that was a parameter error,
    # not an empty folder. (PULL_DISCIPLINE: "an empty result is not evidence of
    # absence; it may be evidence of a typo.")
    q = urllib.parse.urlencode({"widgetId": widget, "folderId": folder,
                                "rootFolderId": root or folder, "accountGUID": ACC})
    st, body = fetch(API + "?" + q)
    if st != 200 or not body:
        return st, None
    try:
        return st, json.loads(body)
    except Exception as e:
        return f"unparseable: {e}", None


RF_TAG = re.compile(r'data-folder-id="([0-9a-f-]{36})"[^>]*data-widget-id="([0-9a-f-]{36})"')


def main():
    BYPASS.mkdir(parents=True, exist_ok=True)
    PDFDIR.mkdir(parents=True, exist_ok=True)
    state = {"started": datetime.now(timezone.utc).isoformat(),
             "control": {}, "pages": {}, "folders": {}, "downloaded": [],
             "already_on_disk_skipped": [], "refused_by_host": []}

    # ---- CONTROL: reproduce a folder we already hold, or stop. -------------
    known = json.loads((GO / "nm_revsharing_files.json").read_text(encoding="utf-8"))
    ctrl_expect = sorted(f["fileId"] for f in known if f["year"] == "2022")
    st, data = widget_files("e204326b-dd87-4532-aa77-0f25a965f1ac",
                            "65484554-ba13-4ca1-87c2-6a24d5f733c7")
    got = sorted(f["fileId"] for f in (((data or {}).get("data") or {}).get("files") or []))
    state["control"] = {"status": st, "expected_fileids": len(ctrl_expect),
                        "returned_fileids": len(got), "match": got == ctrl_expect}
    if not state["control"]["match"]:
        state["stopped"] = "CONTROL_FAILED -- endpoint did not reproduce the 2022 folder"
        (BYPASS / "_nm_recovery_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps(state, indent=2))
        return 2
    print("control OK:", len(got), "fileIds reproduced", flush=True)

    # ---- Harvest folder/widget pairs off the LIVE agency pages -------------
    pairs = {}
    for label, url in (("state_gaming_representative", PAGE), ("quick_facts_archives", QUICKFACTS)):
        st, html = fetch(url)
        state["pages"][label] = {"status": st, "bytes": len(html or "")}
        if st != 200 or not html:
            continue
        (BYPASS / f"gcb_{label}_2026-08-26.html").write_text(html, encoding="utf-8")
        for f, w in RF_TAG.findall(html):
            pairs.setdefault(f, {"widget": w, "pages": []})["pages"].append(label)
    print("folder/widget pairs on live pages:", len(pairs), flush=True)

    seen_folders = set()
    for line in (GO / "nm_revsharing_folders.txt").read_text(encoding="utf-8").splitlines():
        p = line.split("|")
        if len(p) == 4:
            seen_folders.add(p[2])

    # ---- Enumerate each folder --------------------------------------------
    new_files = []
    for folder, meta in pairs.items():
        st, data = widget_files(folder, meta["widget"])
        if st != 200 or not data:
            state["folders"][folder] = {"status": st}
            state["refused_by_host"].append(folder)
            continue
        d = data.get("data") or {}
        files = d.get("files", []) or []
        folders = d.get("folders", []) or []
        (BYPASS / f"nm_folder_listing_{folder}.json").write_text(
            json.dumps(data, indent=1), encoding="utf-8")
        state["folders"][folder] = {
            "status": 200, "widget": meta["widget"], "on_pages": meta["pages"],
            "already_known_folder": folder in seen_folders,
            "n_files": len(files), "n_subfolders": len(folders),
            "file_names": [f.get("name") for f in files][:80],
            "subfolder_names": [f.get("name") for f in folders][:80]}
        for f in files:
            new_files.append({"folder": folder, "widget": meta["widget"],
                              "name": f.get("name"), "fileId": f.get("fileId"),
                              "uploaded_ms": f.get("uploaded")})
        # one level of sub-folders, which is how the year folders are nested
        for sub in folders:
            sid = sub.get("folderId") or sub.get("fileId")
            if not sid:
                continue
            st2, d2 = widget_files(sid, sub.get("widgetId") or meta["widget"],
                                   root=folder)
            if st2 != 200 or not d2:
                state["folders"][sid] = {"status": st2, "parent": folder}
                continue
            sf = ((d2.get("data") or {}).get("files")) or []
            (BYPASS / f"nm_folder_listing_{sid}.json").write_text(
                json.dumps(d2, indent=1), encoding="utf-8")
            state["folders"][sid] = {"status": 200, "parent": folder,
                                     "name": sub.get("name"), "n_files": len(sf),
                                     "file_names": [x.get("name") for x in sf][:80]}
            for f in sf:
                new_files.append({"folder": sid, "widget": meta["widget"],
                                  "parent_folder": folder, "subfolder_name": sub.get("name"),
                                  "name": f.get("name"), "fileId": f.get("fileId"),
                                  "uploaded_ms": f.get("uploaded")})

    (BYPASS / "nm_new_file_index_2026-08-26.json").write_text(
        json.dumps(new_files, indent=1), encoding="utf-8")

    # ---- Download anything that looks like a quarterly release we lack ----
    have = {p.name for p in PDFDIR.glob("*.pdf")}
    want = re.compile(r"(?i)(news release|quarter|revenue shar|quick fact)")
    for f in new_files:
        nm = (f.get("name") or "")
        if not nm.lower().endswith(".pdf") or not want.search(nm):
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", nm)
        out = PDFDIR / f"nmgcb_recovered_{safe}"
        if out.name in have or out.exists():
            state["already_on_disk_skipped"].append(out.name)
            continue
        url = f"{FILEBASE}/{ACC}/{f['fileId']}/{urllib.parse.quote(nm)}"
        st, body = fetch(url, binary=True)
        if st == 200 and body and body[:4] == b"%PDF":
            tmp = out.with_suffix(out.suffix + ".part")
            tmp.write_bytes(body)
            tmp.rename(out)
            state["downloaded"].append({"file": out.name, "url": url, "bytes": len(body)})
            print("  downloaded", out.name, len(body), flush=True)
        else:
            state["refused_by_host"].append({"file": nm, "url": url, "status": st})

    state["finished"] = datetime.now(timezone.utc).isoformat()
    (BYPASS / "_nm_recovery_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items() if k != "folders"}, indent=2)[:4000])
    for k, v in state["folders"].items():
        print(" ", k, v.get("status"), v.get("name") or "", v.get("n_files"),
              (v.get("file_names") or [])[:6])
    return 0


if __name__ == "__main__":
    sys.exit(main())
