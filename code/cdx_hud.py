"""Wayback CDX index queries for HUD ONAP award documents (ICDBG / IHBG-Competitive)."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import fetch, RAW, save_manifest

BASE = ("http://web.archive.org/cdx/search/cdx?url=hud.gov&matchType=domain"
        "&output=json&collapse=urlkey&limit=50000&filter=statuscode:200")

QUERIES = {
    'ihbg':  '.*(?i)ihbg.*',
    'icdbg': '.*(?i)icdbg.*',
    'indianhousing': '.*(?i)(indian.?housing|public_indian_housing/ih).*',
}


def main():
    res = {}
    for tag, pat in QUERIES.items():
        u = BASE + "&filter=original:" + pat
        s, b = fetch(u, "cdx_hud_%s.json" % tag, timeout=420)
        try:
            d = json.loads(b.decode('utf-8', 'replace'))
        except Exception as e:
            print(tag, 'ERR', e, b[:200], flush=True)
            continue
        rows = d[1:]
        res[tag] = rows
        pdfs = [r for r in rows if r[2].lower().split('?')[0].endswith('.pdf')]
        print(tag, s, 'rows', len(rows), 'pdf', len(pdfs), flush=True)
    json.dump(res, open(os.path.join(RAW, 'cdx_hud_all.json'), 'w'))
    save_manifest()


if __name__ == '__main__':
    main()
