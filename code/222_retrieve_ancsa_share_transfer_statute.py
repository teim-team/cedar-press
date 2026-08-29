"""222 — Retrieve, verbatim, the statute that settles the ANCSA share-transfer
question left open in `docs/ANCSA_OWNERSHIP_RULING.md`.

THE QUESTION (owner, 2026-08-26, left open deliberately)
    1. Do adopted persons receive shares?
    2. May shares be gifted to non-Natives?
    3. May shares be gifted to a spouse?

    "Nothing in this repository answers these, and nothing in this repository may
     assume an answer. Reasoning from general principles about ANCSA is exactly
     the failure shape AGENTS.md records under 'a marginal rate cannot be
     inverted' -- the arithmetic is right, the citation is right, and the answer
     is wrong."

WHAT THIS SCRIPT DOES, AND ALL IT DOES
    It fetches four objects from GPO's govinfo and writes their text to disk.  It
    performs NO interpretation.  The reading is in the documents, where a human
    can check it against the same bytes:
        docs/ANCSA_OWNERSHIP_RULING.md   (the answer, appended 2026-08-26)
        docs/UNTAPPED_FREE_SOURCES_2026-08-26.md

WHY FOUR OBJECTS AND NOT ONE
    sec1606  43 U.S.C. 1606(h) -- Settlement Common Stock: the operative text.
    sec1607  43 U.S.C. 1607(c) -- WITHOUT THIS THE ANSWER IS ABOUT THE WRONG
             CORPORATIONS.  1606 is headed "Regional Corporations"; Cedar's 334
             defects are about VILLAGE corporations.  1607(c) is the bridge.
    sec1602  the definitions of "Native" (b) and "Descendant of a Native" (r).
             Question 1 is decided in 1602(r)(2), not in 1606 at all.
    STATUTE-101-Pg1788   Pub. L. 100-241, so the Act can be cited from the
             Statutes at Large and its enactment date read off the source rather
             than from the popular name.  The Act is TITLED "Amendments of 1987"
             and was enacted 1988-02-03; that discrepancy is in the ruling doc.

ACCESS
    api.govinfo.gov is fronted by api.data.gov, so the existing api.data.gov key
    works, exactly as code/147 records for api.fac.gov.  Measured 2026-08-26:
    X-Ratelimit-Limit 36000.  Public, key-free equivalents of every object are
    written into the manifest so a reader with no key can check the quotations.

    Honours logs/_HOSTLOCK_api.govinfo.gov.json.

py -3 code/222_retrieve_ancsa_share_transfer_statute.py
"""
import csv, datetime, html, json, os, pathlib, re, sys, time
import urllib.request, urllib.error

ROOT = pathlib.Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = ROOT / "data" / "raw" / "external" / "untapped_2026-08-26"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)

SCRIPT = "222_retrieve_ancsa_share_transfer_statute.py"
HOST = "api.govinfo.gov"
KEY = os.environ.get("API_DATA_GOV_KEY", "xAmmmCQ05iWdMTWfhvBeSgul008UxCUfSsdZRbex")
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
GAP = 1.6
TODAY = "2026-08-26"

USCODE_PKG = "USCODE-2024-title43"
SECTIONS = [
    ("sec1606", "USCODE-2024-title43-chap33-sec1606",
     "43 U.S.C. 1606 -- Regional Corporations (ANCSA sec. 7). Subsection (h) is "
     "Settlement Common Stock: the alienability restrictions and the closed list "
     "of permitted inter vivos gift recipients."),
    ("sec1607", "USCODE-2024-title43-chap33-sec1607",
     "43 U.S.C. 1607 -- Village Corporations (ANCSA sec. 8). Subsection (c) "
     "applies 1606(g), (h) other than par. (4), and (o) to Village, Urban and "
     "Group Corporations. This is the bridge to Cedar's population."),
    ("sec1602", "USCODE-2024-title43-chap33-sec1602",
     "43 U.S.C. 1602 -- Definitions. (b) 'Native', (r) 'Descendant of a Native' "
     "including the adoptee clause, (s) 'Alienability restrictions'."),
    ("sec1629c", "USCODE-2024-title43-chap33-sec1629c",
     "43 U.S.C. 1629c -- Termination of alienability restrictions. RETRIEVED AND "
     "DELIBERATELY UNREAD as of 2026-08-26: it is the reason the statutory answer "
     "is a FLOOR and not the operative answer for a given corporation."),
]
STATUTE = ("STATUTE-101", "STATUTE-101-Pg1788",
           "Pub. L. 100-241, Alaska Native Claims Settlement Act Amendments of "
           "1987, 101 Stat. 1788. dateIssued 1988-02-03.")


def log(m):
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode(), flush=True)


def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            log(f"HOSTLOCK held by {cur.get('script')}; queued and exiting")
            cur.setdefault("queue", []).append({"script": f"code/{SCRIPT}", "note": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            return False
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{SCRIPT}",
        "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active": True, "queue": [], "note": note,
        "policy": f"sequential, single stream, >={GAP}s gap, no retry loop",
    }, indent=1), encoding="utf-8")
    return True


def release_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"host": HOST}
    cur.update(active=False,
               released=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               note=note)
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


def fetch(url, dest):
    """Return (status, bytes_written). .part then rename: an interruption must
    not look like a completion."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        return e.code, 0
    tmp = str(dest) + ".part"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, dest)
    return status, len(body)


def to_text(src, dest):
    t = src.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<pre.*?>(.*?)</pre>", t, re.S | re.I)
    body = html.unescape(re.sub(r"<[^>]+>", "", m.group(1) if m else t))
    tmp = str(dest) + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, dest)
    return len(body)


def main():
    if not claim_host("ANCSA sec. 7(h) share-transfer statute retrieval"):
        return 3
    manifest = []
    try:
        for name, granule, why in SECTIONS:
            api = (f"https://api.govinfo.gov/packages/{USCODE_PKG}/granules/"
                   f"{granule}/htm?api_key={KEY}")
            pub = (f"https://www.govinfo.gov/content/pkg/{USCODE_PKG}/html/"
                   f"{granule}.htm")
            dest = OUT / f"{granule}.htm"
            status, n = fetch(api, dest)
            chars = to_text(dest, OUT / f"{name}.txt") if status == 200 else 0
            log(f"  {name:9s} HTTP {status}  {n:>7,} bytes  {chars:>7,} chars text")
            manifest.append(dict(object=name, granule_id=granule,
                                 http_status=status, bytes=n, text_chars=chars,
                                 api_url=api.split("?api_key")[0],
                                 public_url=pub, why=why,
                                 retrieved_date=TODAY))
            time.sleep(GAP)

        pkg, gran, why = STATUTE
        api = (f"https://api.govinfo.gov/packages/{pkg}/granules/{gran}/pdf"
               f"?api_key={KEY}")
        pub = f"https://www.govinfo.gov/content/pkg/{pkg}/pdf/{gran}.pdf"
        dest = OUT / f"{gran}.pdf"
        status, n = fetch(api, dest)
        log(f"  {gran:9s} HTTP {status}  {n:>7,} bytes")
        manifest.append(dict(object=gran, granule_id=gran, http_status=status,
                             bytes=n, text_chars="",
                             api_url=api.split("?api_key")[0],
                             public_url=pub, why=why, retrieved_date=TODAY))
    finally:
        release_host("ANCSA statute retrieval complete")

    path = OUT / "_222_ancsa_statute_manifest.csv"
    tmp = str(path) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        w.writerows(manifest)
    os.replace(tmp, path)
    log(f"wrote {path}")

    bad = [m for m in manifest if m["http_status"] != 200]
    if bad:
        log(f"REFUSED: {[(m['object'], m['http_status']) for m in bad]}")
        return 1
    log("all objects HTTP 200. The reading is in "
        "docs/ANCSA_OWNERSHIP_RULING.md; this script asserts nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
