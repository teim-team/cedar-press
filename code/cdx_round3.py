import sys, json, os, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import fetch, RAW, save_manifest


def cdx(u, f=None, tries=4):
    for i in range(tries):
        s, b = fetch(u, f, timeout=420)
        try:
            return json.loads(b.decode('utf-8', 'replace'))[1:]
        except Exception:
            time.sleep(15)
    return []


Q = [
    ('eda_news_tribal',
     "http://web.archive.org/cdx/search/cdx?url=eda.gov&matchType=domain&output=json&collapse=urlkey"
     "&limit=20000&filter=statuscode:200&filter=original:.*(?i)(tribe|tribal|nation|pueblo|indian).*"),
    ('hud_awardpdf2',
     "http://web.archive.org/cdx/search/cdx?url=hud.gov/sites/dfiles*&output=json&collapse=urlkey"
     "&limit=30000&filter=statuscode:200&filter=original:.*(?i)(icdbg|ihbg).*"),
]

for tag, u in Q:
    rows = cdx(u, "cdx_%s.json" % tag)
    print('###', tag, 'rows', len(rows), flush=True)
    for r in sorted(rows, key=lambda x: x[2]):
        if re.search(r'(award|grantee|selectee|press-release|news)', r[2], re.I):
            print('   ', r[1], r[2][:180], flush=True)
    time.sleep(5)
save_manifest()
