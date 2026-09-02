"""Rebuild _SOURCE_MANIFEST.csv so every file in federal_award_lists/ is accounted for."""
import os, sys, csv, glob, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import RAW

MP = os.path.join(RAW, '_SOURCE_MANIFEST.csv')
have = {}
if os.path.exists(MP):
    with open(MP, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            have[r['file']] = r

DERIVED = {
    'tbcp_awards_from_press_releases.csv':
        'DERIVED - parsed from the ntia_pr_*.html files by code/parse_tbcp.py',
    'tbcp_awardee_pages.csv':
        'DERIVED - scraped by code/scrape_tbcp_awardees.py from broadbandusa.ntia.gov awardee pages',
    'doe_indian_energy_project_details.csv':
        'DERIVED - scraped by code/scrape_doe_indian_energy.py from energy.gov project pages',
    'doe_indian_energy_over1m.csv':
        'DERIVED - subset of doe_indian_energy_project_details.csv with DOE share >= $1M',
    'hud_onap_awards_parsed.csv':
        'DERIVED - parsed from the hud_*.pdf files by code/parse_hud_awards.py',
    'doe_ie_export.csv':
        'https://docs.google.com/spreadsheets/d/1PeYaVWqSWABu6kWKI3VF48_iL-YLAyFJIo9j8Hnx73Y/export?format=csv&gid=0'
        ' (data source of the DOE Tribal Energy Projects Database map app)',
    'doe_indian_energy_projects.csv':
        'https://docs.google.com/spreadsheets/d/1PeYaVWqSWABu6kWKI3VF48_iL-YLAyFJIo9j8Hnx73Y/gviz/tq?tqx=out:csv&sheet=Data',
    'tbcp_landing.html': 'https://broadbandusa.ntia.gov/funding-programs/tribal-broadband-connectivity',
    'tbcp_r1_awards.html': 'https://broadbandusa.ntia.gov/funding-programs/tribal-broadband-connectivity-round-1/award-recipients',
    'tbcp_r2_awards.html': 'https://broadbandusa.ntia.gov/funding-programs/tribal-broadband-connectivity-round-2/award-recipients',
    'tbcp_r3_awards.html': 'https://broadbandusa.ntia.gov/funding-programs/tribal-broadband-connectivity/award-recipients',
    'tbcp_news.html': 'https://broadbandusa.ntia.gov/tribal-broadband-connectivity-program/latest-news',
    'tbcp_news_index.json': 'DERIVED - link index parsed from the TBCP news listing pages',
    'tbcp_news_index.txt': 'DERIVED - text form of tbcp_news_index.json',
    'ntia_news_all_index.json': 'DERIVED - full broadbandusa.ntia.gov/news/latest-news link index (328 items, 39 pages)',
    'ntia_news_dates.json': 'DERIVED - publication date per news item, read off the news listing pages',
    'ntia_pr_index.json': 'DERIVED - first-pass press-release index',
    'ntia_pr_dates.json': 'DERIVED - first-pass date/table diagnostics',
    'ntia_pr_162m.html': 'https://broadbandusa.ntia.gov/news/latest-news/biden-harris-administration-recommends-award-more-162-million-expand-internet-use (DUPLICATE of ntia_pr_biden-harris-administration-recommends-award-more-16*.html; excluded from parsing)',
    'pr_162m.html': 'same URL as ntia_pr_162m.html - early probe copy',
    'pr_162m.txt': 'DERIVED - text extraction of pr_162m.html',
    'sample_detail.html': 'https://broadbandusa.ntia.gov/funding-programs/tribal-broadband-connectivity-program-round-1/awardee/tribal-broadband-connectivity-program-3',
    'doe_projects_db.html': 'https://www.energy.gov/indianenergy/tribal-energy-projects-database',
    'doe_map_app.html': 'https://natlabrockies.github.io/eere-ie-projects-map/',
    'doe_app_es6.js': 'https://raw.githubusercontent.com/natlabrockies/eere-ie-projects-map/HEAD/src/client/js/app.es6.js',
    'doe_repo_tree.json': 'https://api.github.com/repos/natlabrockies/eere-ie-projects-map/git/trees/HEAD?recursive=1',
    'doe_sample_project.html': 'https://www.energy.gov/node/4849819',
    'eda_arpa_indigenous.html': 'https://www.eda.gov/arpa/indigenous-communities',
    'eda_ic_fact_sheet.pdf': 'https://www.eda.gov/sites/default/files/2022-11/IC_Fact%20Sheet.pdf',
    'eda_arp_impact.html': 'https://www.eda.gov/arpa/impact (HTTP 403 - Cloudflare challenge page saved as the negative result)',
    'eda_arp_impact_archived.html': 'https://web.archive.org/web/20230425224704id_/https://www.eda.gov/archives/2022/arpa/impact/',
    'eda_arch_20230930120614.html': 'https://web.archive.org/web/20230930120614id_/https://www.eda.gov/archives/2022/arpa/indigenous/index.htm',
    'eda_arch_20221217173922.html': 'https://web.archive.org/web/20221217173922id_/https://www.eda.gov/funding/programs/american-rescue-plan/indigenous-communities',
    'gao_24_106541.pdf': 'https://www.gao.gov/assets/gao-24-106541.pdf (HTTP 403 - REFUSED; the saved file is the 405-byte block page, NOT the report)',
    'hud_icdbg_live.html': 'https://www.hud.gov/program_offices/public_indian_housing/ih/grants/icdbg (live page, content emptied by the 2025-26 reorg)',
    'dg_tbcp.json': 'https://catalog.data.gov/api/3/action/package_search?q=tribal+broadband+connectivity (HTTP 404 - endpoint retired)',
    'cdx_dfiles_pih.json': 'http://web.archive.org/cdx/search/cdx?url=hud.gov/sites/dfiles/PIH*&output=json&collapse=urlkey&limit=20000&filter=statuscode:200',
    'cdx_onap_path.json': 'http://web.archive.org/cdx/search/cdx?url=hud.gov/program_offices/public_indian_housing/ih*&output=json&collapse=urlkey&limit=20000&filter=statuscode:200',
    'cdx_hud_all.json': 'DERIVED - combined output of the first (partly rate-limited) HUD CDX pass',
    'cdx_hud_more.json': 'DERIVED - empty; the prefix CDX pass was rate-limited and returned nothing',
}

rows = []
today = datetime.date.today().isoformat()
for p in sorted(glob.glob(os.path.join(RAW, '*'))):
    name = os.path.basename(p)
    if name == '_SOURCE_MANIFEST.csv' or os.path.isdir(p):
        continue
    r = have.get(name)
    if r:
        rows.append(r)
        continue
    url = DERIVED.get(name, '')
    if not url:
        if name.startswith('ntia_pr_') and name.endswith('.txt'):
            url = 'DERIVED - text extraction of ' + name[:-4] + '.html'
        elif name.startswith('doe_project_') and name.endswith('.txt'):
            url = 'DERIVED - text extraction of ' + name[:-4] + '.html'
        elif name.startswith('hud_') and name.endswith('.txt'):
            url = 'DERIVED - pypdf text extraction of ' + name[:-4] + '.pdf'
        elif name.startswith('eda_') and name.endswith('.txt'):
            url = 'DERIVED - pypdf text extraction of ' + name[:-4] + '.pdf'
        else:
            url = 'UNRECORDED - see docs/FEDERAL_AWARD_LISTS_LOG.md'
    rows.append(dict(file=name, url=url, http_status='', bytes=os.path.getsize(p),
                     fetched_date=today))

with open(MP, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['file', 'url', 'http_status', 'bytes', 'fetched_date'])
    w.writeheader()
    w.writerows(rows)
print('manifest rows', len(rows))
