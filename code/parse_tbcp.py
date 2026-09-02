"""Parse NTIA TBCP press releases into an award table.

Every field is transcribed from the retrieved HTML in
data/raw/external/federal_award_lists/ntia_pr_*.html. Nothing is inferred.
"""
import re, os, glob, html, csv, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import RAW, text

DATE = re.compile(r'(January|February|March|April|May|June|July|August|September|'
                  r'October|November|December)\s+(\d{1,2}),?\s+(\d{4})')
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}


def rel_date(t):
    m = re.search(r'Immediate Release:?', t, re.I)
    if not m:
        return None
    m2 = DATE.search(t, m.end())
    if m2 and m2.start() - m.end() < 100:
        return "%s-%02d-%02d" % (m2.group(3), MONTHS[m2.group(1)], int(m2.group(2)))
    return None


def tables(b):
    out = []
    for tb in re.findall(r'<table.*?</table>', b, re.S | re.I):
        rows = []
        for tr in re.findall(r'<tr.*?</tr>', tb, re.S | re.I):
            cells = [html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c))).strip()
                     for c in re.findall(r'<t[dh].*?</t[dh]>', tr, re.S | re.I)]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def classify(h):
    h = h.lower().strip()
    if h.startswith('applicant') or h in ('recipient', 'awardee', 'entity', 'tribe'):
        return 'applicant'
    if 'amount' in h:
        return 'amount'
    if h in ('location', 'state', 'state(s)', 'states'):
        return 'location'
    if 'type' in h:
        return 'ptype'
    if 'description' in h or 'project' in h:
        return 'desc'
    return None


AMT = re.compile(r'^\$?([\d,]+(?:\.\d{1,2})?)$')


def main():
    recs = []
    diag = []
    for f in sorted(glob.glob(os.path.join(RAW, 'ntia_pr_*.html'))):
        raw = open(f, 'rb').read()
        b = raw.decode('utf-8', 'replace')
        t = text(raw)
        d = rel_date(t)
        title = None
        m = re.search(r'<title>(.*?)</title>', b, re.S | re.I)
        if m:
            title = html.unescape(re.sub(r'\s+', ' ', m.group(1))).replace(' | BroadbandUSA', '').strip()
        n = 0
        for tb in tables(b):
            hdr = [classify(c) for c in tb[0]]
            if 'applicant' not in hdr:
                continue
            for row in tb[1:]:
                if len(row) != len(hdr):
                    continue
                rec = {}
                for k, v in zip(hdr, row):
                    if k:
                        rec[k] = v
                app = rec.get('applicant', '').strip()
                if not app or app.lower() in ('applicant', 'total'):
                    continue
                amt = rec.get('amount', '').strip()
                val = ''
                if amt:
                    mm = AMT.match(amt.replace(' ', '').strip())
                    if mm:
                        val = mm.group(1).replace(',', '')
                recs.append(dict(applicant=app, amount_raw=amt, amount=val,
                                 location=rec.get('location', ''),
                                 ptype=rec.get('ptype', ''),
                                 desc=rec.get('desc', ''),
                                 release_date=d or '', release_title=title or '',
                                 source_file=os.path.basename(f)))
                n += 1
        diag.append((os.path.basename(f), d, n))

    out = os.path.join(RAW, 'tbcp_awards_from_press_releases.csv')
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['applicant', 'amount', 'amount_raw', 'location',
                                           'ptype', 'desc', 'release_date', 'release_title',
                                           'source_file'])
        w.writeheader()
        w.writerows(recs)
    print('rows', len(recs), '->', out)
    dated = [r for r in recs if r['release_date']]
    valued = [r for r in dated if r['amount']]
    print('dated', len(dated), 'dated+valued', len(valued))
    print('>=1M', len([r for r in valued if float(r['amount']) >= 1e6]))
    for x in diag:
        print('  ', x)


if __name__ == '__main__':
    main()
