import requests, re, time
from bs4 import BeautifulSoup
BASE="https://portal.akdbsstar.us/StarWebPortal/"
SEARCH=BASE+"page/ANCSA/portal.aspx"
P="ctl00$ContentPlaceholder1$PortalPageControl1$ctl26$"
GRID=P+"gvFileList"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
DELAY=1.5

def new_session():
    s=requests.Session(); s.headers.update({"User-Agent":UA,
      "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language":"en-US,en;q=0.9"})
    s.get(BASE+"page/default/portal.aspx",timeout=60); time.sleep(DELAY)
    return s

def hidden(h):
    soup=BeautifulSoup(h,"html.parser"); d={}
    for i in soup.find_all("input",{"type":"hidden"}):
        n=i.get("name")
        if n is not None: d[n]=i.get("value","")
    return d

def parse_results(h):
    soup=BeautifulSoup(h,"html.parser")
    pos=soup.find(id="ctl00_ContentPlaceholder1_PortalPageControl1_ctl26_lblGridPosition")
    postxt=pos.get_text(strip=True) if pos else ""
    tbl=soup.find(id="ctl00_ContentPlaceholder1_PortalPageControl1_ctl26_gvFileList")
    rows=[]
    if tbl:
        for tr in tbl.find_all("tr"):
            a=tr.find("a",id=re.compile("FileHyperLink$"))
            if not a: continue
            href=a.get("href","")
            m=re.search(r"Id=([0-9a-fA-F-]{36})",href)
            tds=tr.find_all("td")
            yr=tr.find("span",id=re.compile("lblYear$"))
            cat=tr.find("span",id=re.compile("lblCategory$"))
            rows.append({"desc":a.get_text(strip=True),
                         "doc_id":m.group(1) if m else "",
                         "url":BASE+"ViewFile.aspx?Id="+(m.group(1) if m else ""),
                         "year":yr.get_text(strip=True) if yr else "",
                         "category":cat.get_text(strip=True) if cat else ""})
    pages=set()
    if tbl:
        for a in tbl.find_all("a",href=re.compile(r"Page\$\d+")):
            pages.add(int(re.search(r"Page\$(\d+)",a["href"]).group(1)))
    err=[]
    for sp in soup.find_all("span",style=re.compile("color:Red",re.I)):
        t=sp.get_text(strip=True)
        if t: err.append(t)
    return postxt, rows, sorted(pages), err

def search(s, corp=None, cat=None, year=None):
    r=s.get(SEARCH,timeout=60); time.sleep(DELAY)
    d=hidden(r.text)
    d[P+"ddCorporationName"]= corp or "-----Select Corporation Name-----"
    d[P+"ddDocumentCategory"]= cat or "-----Select Document Category-----"
    d[P+"txtYear"]= year or ""
    d[P+"btnSubmit"]="Submit"
    r2=s.post(SEARCH,data=d,timeout=120,headers={"Referer":SEARCH}); time.sleep(DELAY)
    all_rows=[]; postxt,rows,pages,err=parse_results(r2.text)
    all_rows+=rows
    cur=r2
    done={1}
    while True:
        _,_,pages,_=parse_results(cur.text)
        nxt=[p for p in pages if p not in done]
        if not nxt: break
        p=nxt[0]; done.add(p)
        d2=hidden(cur.text)
        d2["__EVENTTARGET"]=GRID; d2["__EVENTARGUMENT"]="Page$%d"%p
        d2[P+"ddCorporationName"]=corp or "-----Select Corporation Name-----"
        d2[P+"ddDocumentCategory"]=cat or "-----Select Document Category-----"
        d2[P+"txtYear"]=year or ""
        cur=s.post(SEARCH,data=d2,timeout=120,headers={"Referer":SEARCH}); time.sleep(DELAY)
        _,rows2,_,_=parse_results(cur.text)
        all_rows+=rows2
    # dedupe
    seen=set(); out=[]
    for x in all_rows:
        if x["doc_id"] in seen: continue
        seen.add(x["doc_id"]); out.append(x)
    return postxt, out, err
S=new_session()
