#!/usr/bin/env python3
"""
Cedar Press - 90: retrieve the NIGC Office of General Counsel declination-letter
archive (index + every posted PDF).

WHAT A DECLINATION LETTER IS
----------------------------
NIGC OGC reviews *unexecuted* agreements a tribe submits voluntarily and issues
an opinion on whether the documents constitute a MANAGEMENT CONTRACT requiring
the Chair's approval under IGRA, and whether they violate IGRA's sole
proprietary interest requirement. In NIGC's own words on the index page:

    "This review is neither required by the Indian Gaming Regulatory Act nor
     the NIGC regulations and is offered by the OGC as a courtesy."

    "Documents should be submitted prior to their execution (unsigned) as the
     General Counsel will not provide a declination letter for executed
     documents."

Those two sentences are the whole evidentiary limit of this layer and they are
the agency's own. A declination letter proves NIGC REVIEWED SUBMITTED DRAFTS.
It does not prove the deal closed, the property opened, or the land is in
trust. And because review is voluntary and posting is subject to a FOIA
release review, ABSENCE FROM THIS ARCHIVE PROVES NOTHING.

THE DOWNLOAD TRAP (recorded in docs/NIGC_REGION_BUILD_LOG.md §15)
------------------------------------------------------------------
On nigc.gov every `/download/<slug>/` landing page carries a sidebar WPDM link
with the SAME `wpdmdl=3974`, so taking the first `wpdmdl=` match returns the
identical PDF every time, all the same byte length, looking like success.

Here the index table links WPDM ids directly, so the trap presents differently:
the page's FIRST two `wpdmdl=` links are the sidebar (`wpdmdl=3974`) and the
"Helpful Hints" doc (`wpdmdl=7374`), neither of which is a declination letter.
This script therefore takes links only from inside `<table id="tablepress-2">`,
resolves each 302 to its real `wp-content/uploads/.../<filename>.pdf`, and
REFUSES to write a file whose md5 duplicates one already written under a
different opinion id without recording the collision.

PULL DISCIPLINE
---------------
One poller, one host. `logs/_HOSTLOCK_www.nigc.gov.json` is claimed before the
first request; sequential requests with a 2 s floor gap; exponential backoff
60/120/240... on failure; checkpoint written before the first request so a
killed run loses nothing.

Writes data/raw/external/nigc_declinations/_index/declination_letters_index.html
       data/raw/external/nigc_declinations/_index/declination_letters_index.csv
       data/raw/external/nigc_declinations/pdf/<filename>.pdf
       data/raw/external/nigc_declinations/_SOURCE_MANIFEST.csv
       data/raw/external/nigc_declinations/_fetch_state.json
"""

import csv
import hashlib
import html as htmllib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "external" / "nigc_declinations"
IDX = RAW / "_index"
PDFDIR = RAW / "pdf"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "www.nigc.gov"
LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
STATE = RAW / "_fetch_state.json"
INDEX_URL = ("https://www.nigc.gov/office-of-general-counsel/legal-opinions/"
             "declination-letters/")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 2.0

# WPDM ids that are NOT declination letters. Both live on the index page and
# both would be picked up by a naive "first wpdmdl= on the page" scrape.
NON_LETTER_WPDMDL = {"3974", "7374"}


def curl(url, out_path=None, timeout=120):
    """Return (status, effective_url, bytes_or_None). Follows redirects."""
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "--max-time", str(timeout),
           "-w", "%{http_code}\t%{url_effective}", url]
    if out_path:
        cmd[1:1] = ["-o", str(out_path)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        tail = (p.stdout or "").strip().split("\t")
        status = int(tail[0]) if tail and tail[0].isdigit() else 0
        eff = tail[1] if len(tail) > 1 else ""
        return status, eff, None
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"(\d{3})\t(\S*)$", out)
    if not m:
        return 0, "", out
    return int(m.group(1)), m.group(2).decode("utf-8", "replace"), out[:m.start()]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def claim_lock(queue):
    if LOCK.exists():
        try:
            cur = json.load(open(LOCK))
        except Exception:
            cur = {}
        pid = cur.get("pid")
        alive = False
        if pid:
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                               capture_output=True, text=True)
            alive = str(pid) in (r.stdout or "")
        started = cur.get("started", "")
        stale = True
        try:
            age = (datetime.utcnow() - datetime.fromisoformat(
                started.rstrip("Z"))).total_seconds()
            stale = age > 6 * 3600
        except Exception:
            pass
        if alive and not stale and cur.get("script") != "code/90_fetch_nigc_declinations.py":
            cur.setdefault("queue", []).extend(queue)
            json.dump(cur, open(LOCK, "w"), indent=1)
            print(f"HOSTLOCK held by {cur.get('script')} (pid {pid}); "
                  f"queued work and exiting per docs/PULL_DISCIPLINE.md rule 1.")
            sys.exit(0)
    LOGS.mkdir(parents=True, exist_ok=True)
    json.dump({"host": HOST, "pid": os.getpid(),
               "script": "code/90_fetch_nigc_declinations.py",
               "started": datetime.utcnow().isoformat() + "Z",
               "queue": queue}, open(LOCK, "w"), indent=1)


def parse_index(text):
    """Rows from tablepress-2 only. Nothing outside the table is a letter."""
    m = re.search(r'<table id="tablepress-2".*?</table>', text, re.S)
    if not m:
        raise SystemExit("tablepress-2 not found - index layout changed.")
    tab = m.group(0)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tab, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 3:
            continue

        def flat(x):
            return re.sub(r"\s+", " ",
                          htmllib.unescape(re.sub("<[^>]+>", " ", x))).strip()

        d = flat(tds[0])
        tribe = flat(tds[1])
        company = flat(tds[2])
        href = re.search(r'href="([^"]+)"', tds[1])
        url = htmllib.unescape(href.group(1)) if href else ""
        wp = re.search(r"wpdmdl=(\d+)", url)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        rows.append({"index_date": d, "index_tribe": tribe,
                     "index_company": company, "wpdm_url": url,
                     "wpdmdl": wp.group(1) if wp else ""})
    return rows


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    IDX.mkdir(parents=True, exist_ok=True)
    PDFDIR.mkdir(parents=True, exist_ok=True)
    claim_lock(["declination_index", "declination_pdfs"])

    state = json.load(open(STATE)) if STATE.exists() else {"done": {}}
    json.dump(state, open(STATE, "w"), indent=1)  # checkpoint before request 1

    idx_html = IDX / "declination_letters_index.html"
    if not idx_html.exists() or "--refetch-index" in sys.argv:
        st, eff, body = curl(INDEX_URL)
        print(f"index {st} {eff} {len(body or b'')} bytes")
        if st != 200:
            raise SystemExit("index fetch failed")
        idx_html.write_bytes(body)
        time.sleep(GAP)
    text = idx_html.read_text(encoding="utf-8", errors="replace")
    rows = parse_index(text)
    print(f"index rows: {len(rows)}  "
          f"{min(r['index_date'] for r in rows)} .. "
          f"{max(r['index_date'] for r in rows)}")

    # Stable Cedar opinion id: date + zero-padded sequence within that date,
    # assigned on the index's own order. Never derived from the WPDM id, which
    # is a CMS artefact and changes when a file is re-uploaded.
    seq = {}
    for r in rows:
        n = seq.get(r["index_date"], 0) + 1
        seq[r["index_date"]] = n
        r["cedar_opinion_id"] = f"NIGC-DL-{r['index_date'].replace('-', '')}-{n:02d}"

    with open(IDX / "declination_letters_index.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "cedar_opinion_id", "index_date", "index_tribe", "index_company",
            "wpdmdl", "wpdm_url"])
        w.writeheader()
        w.writerows(rows)

    manifest = []
    mpath = RAW / "_SOURCE_MANIFEST.csv"
    if mpath.exists():
        with open(mpath, encoding="utf-8-sig", newline="") as fh:
            manifest = list(csv.DictReader(fh))
    have = {m["cedar_opinion_id"]: m for m in manifest}
    by_md5 = {m["md5"]: m["cedar_opinion_id"] for m in manifest if m.get("md5")}

    backoff = 60
    fails = 0
    for i, r in enumerate(rows, 1):
        oid = r["cedar_opinion_id"]
        if oid in have and (PDFDIR / have[oid]["local_name"]).exists():
            continue
        if not r["wpdm_url"]:
            print(f"  {oid}: no link on the index row - skipped")
            continue
        if r["wpdmdl"] in NON_LETTER_WPDMDL:
            print(f"  {oid}: wpdmdl={r['wpdmdl']} is the sidebar/helpful-hints "
                  f"doc, not a letter - refused")
            continue
        url = r["wpdm_url"]
        if url.startswith("https://www.nigc.gov?"):
            url = url.replace("https://www.nigc.gov?", "https://www.nigc.gov/?")
        tmp = PDFDIR / f"_tmp_{oid}.pdf"
        st, eff, _ = curl(url, out_path=tmp)
        # `eff` is the resolved wp-content URL; its basename is the real filename.
        fname = os.path.basename(eff.split("?")[0]) or f"{oid}.pdf"
        if not fname.lower().endswith(".pdf"):
            fname = f"{oid}.pdf"
        ok = st == 200 and tmp.exists() and tmp.stat().st_size > 2000
        head = tmp.read_bytes()[:5] if tmp.exists() else b""
        if ok and head != b"%PDF-":
            ok = False
        if not ok:
            fails += 1
            print(f"  {oid}: FAILED status={st} size="
                  f"{tmp.stat().st_size if tmp.exists() else 0}")
            if tmp.exists():
                tmp.unlink()
            time.sleep(backoff)
            backoff = min(backoff * 2, 1800)
            if backoff > 1700:
                print("backing off past 30 min - stopping, per PULL_DISCIPLINE")
                break
            continue
        backoff = 60
        digest = md5(tmp)
        collision = by_md5.get(digest)
        target = PDFDIR / fname
        if target.exists() and md5(target) != digest:
            target = PDFDIR / f"{Path(fname).stem}__{oid}.pdf"
        os.replace(tmp, target)
        by_md5.setdefault(digest, oid)
        rec = {"cedar_opinion_id": oid,
               "local_path": str(target.relative_to(CEDAR)).replace("\\", "/"),
               "local_name": target.name,
               "source_host": HOST,
               "source_url": r["wpdm_url"],
               "resolved_url": eff,
               "retrieval_note": ("WPDM link taken from inside tablepress-2 on "
                                  "the declination-letters index; 302 resolved "
                                  "to the wp-content object"),
               "bytes": target.stat().st_size,
               "md5": digest,
               "md5_duplicate_of": collision or "",
               "index_date": r["index_date"],
               "index_tribe": r["index_tribe"],
               "index_company": r["index_company"],
               "http_status": st,
               "fetched_date": TODAY}
        manifest = [m for m in manifest if m["cedar_opinion_id"] != oid] + [rec]
        have[oid] = rec
        state["done"][oid] = digest
        if i % 10 == 0 or i == len(rows):
            with open(mpath, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rec.keys()))
                w.writeheader()
                w.writerows(manifest)
            json.dump(state, open(STATE, "w"), indent=1)
            print(f"  [{i}/{len(rows)}] {oid} {target.name} "
                  f"{rec['bytes']:,}B {digest[:8]}"
                  + ("  DUPLICATE-MD5" if collision else ""))
        time.sleep(GAP)

    if manifest:
        fields = list(manifest[-1].keys())
        with open(mpath, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(manifest)
    json.dump(state, open(STATE, "w"), indent=1)

    dupes = [m for m in manifest if m.get("md5_duplicate_of")]
    print(f"\nretrieved {len(manifest)} of {len(rows)} index rows; "
          f"{len(set(m['md5'] for m in manifest))} distinct md5s; "
          f"{len(dupes)} md5 collisions; {fails} failures")
    if LOCK.exists():
        LOCK.unlink()
        print("host lock released")


if __name__ == "__main__":
    main()
