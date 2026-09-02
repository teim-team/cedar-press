"""Scrape every TBCP awardee detail page (Round 1 + Round 2) from broadbandusa.ntia.gov.

Yields recipient name, project title, funding amount and state. These pages carry NO date;
dates come from the NTIA press releases (see parse_tbcp.py).
"""
import re, os, html, csv, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import fetch, RAW, save_manifest, text

BASE = "https://broadbandusa.ntia.gov"
INDEX = {
    "TBCP I": "/funding-programs/tribal-broadband-connectivity-round-1/award-recipients",
    "TBCP II": "/funding-programs/tribal-broadband-connectivity-round-2/award-recipients",
}

AMT = re.compile(r'\$([\d,]+(?:\.\d{2})?)')


def links(round_name, path):
    s, b = fetch(BASE + path)
    t = b.decode('utf-8', 'replace')
    out = []
    for h, x in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        name = html.unescape(re.sub(r'<[^>]+>', '', x)).strip()
        if '/awardee/' in h and name.endswith('(%s)' % round_name):
            out.append((h, name))
    return list(dict.fromkeys(out))


def main():
    rows = []
    for rnd, path in INDEX.items():
        ls = links(rnd, path)
        print(rnd, 'awardee links', len(ls), flush=True)
        for i, (h, name) in enumerate(ls):
            s, b = fetch(BASE + h)
            t = text(b)
            amt = ''
            m = re.search(r'\$([\d,]+(?:\.\d{2})?)\s*\n\s*Funding Amount', t)
            if not m:
                m = re.search(r'Funding Amount\s*\n\s*\$([\d,]+(?:\.\d{2})?)', t)
            if m:
                amt = m.group(1).replace(',', '')
            st = ''
            m2 = re.search(r'State\(s\):\s*\n(.+)', t)
            if m2:
                st = m2.group(1).strip()
            pt = ''
            m3 = re.search(r'Project Title:\s*\n(.+)', t)
            if m3:
                pt = m3.group(1).strip()
            rows.append(dict(round=rnd, awardee=name, project_title=pt,
                             amount=amt, states=st, url=BASE + h, http=s))
            if i % 25 == 0:
                print(' ', rnd, i, name[:50], amt, flush=True)
    out = os.path.join(RAW, 'tbcp_awardee_pages.csv')
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['round', 'awardee', 'project_title', 'amount',
                                          'states', 'url', 'http'])
        w.writeheader()
        w.writerows(rows)
    print('WROTE', len(rows), out)
    print('with amount', len([r for r in rows if r['amount']]))


if __name__ == '__main__':
    main()
