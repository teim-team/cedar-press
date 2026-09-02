import requests, re, time
from bs4 import BeautifulSoup
BASE="https://portal.akdbsstar.us/StarWebPortal/"
SEARCH=BASE+"page/ANCSA/portal.aspx"
P="ctl00$ContentPlaceholder1$PortalPageControl1$ctl26$"
GRID=P+"gvFileList"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
DELAY=1.0
NOCORP="-----Select Corporation Name-----"
NOCAT="-----Select Document Category-----"

class Portal:
    def __init__(self):
        self.s=requests.Session()
        self.s.headers.update({"User-Agent":UA,
          "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language":"en-US,en;q=0.9"})
        self.s.get(BASE+"page/default/portal.aspx",timeout=60); time.sleep(DELAY)
        r=self.s.get(SEARCH,timeout=60); time.sleep(DELAY)
        self.last=r.text
    def _hidden(self,h):
        soup=BeautifulSoup(h,"html.parser"); d={}
        for i in soup.find_all("input",{"type":"hidden"}):
            n=i.get("name")
            if n is not None: d[n]=i.get("value","")
        return d
    def _post(self,d):
        r=self.s.post(SEARCH,data=d,timeout=240,headers={"Referer":SEARCH})
        time.sleep(DELAY)
        if r.status_code!=200 or "ddCorporationName" not in r.text:
            # session died; rebuild
            self.__init__()
            raise RuntimeError("bad response %s"%r.status_code)
        self.last=r.text
        return r.text
    def search(self,corp=None,cat=None,year=None,paginate=True,maxpages=200):
        d=self._hidden(self.last)
        d.pop("__EVENTTARGET",None); d.pop("__EVENTARGUMENT",None)
        d["__EVENTTARGET"]=""; d["__EVENTARGUMENT"]=""
        d[P+"ddCorporationName"]=corp or NOCORP
        d[P+"ddDocumentCategory"]=cat or NOCAT
        d[P+"txtYear"]=year or ""
        d[P+"btnSubmit"]="Submit"
        h=self._post(d)
        total,rows,pages=parse(h)
        if not paginate: return total,rows
        done={1}
        while len(done)<maxpages:
            _,_,pages=parse(self.last)
            nxt=[p for p in pages if p not in done]
            if not nxt: break
            p=min(nxt); done.add(p)
            d2=self._hidden(self.last)
            d2["__EVENTTARGET"]=GRID; d2["__EVENTARGUMENT"]="Page$%d"%p
            d2[P+"ddCorporationName"]=corp or NOCORP
            d2[P+"ddDocumentCategory"]=cat or NOCAT
            d2[P+"txtYear"]=year or ""
            h2=self._post(d2)
            _,r2,_=parse(h2)
            rows+=r2
        seen=set(); out=[]
        for x in rows:
            if x["doc_id"] in seen: continue
            seen.add(x["doc_id"]); out.append(x)
        return total,out

def parse(h):
    soup=BeautifulSoup(h,"html.parser")
    pos=soup.find(id="ctl00_ContentPlaceholder1_PortalPageControl1_ctl26_lblGridPosition")
    txt=pos.get_text(strip=True) if pos else ""
    m=re.search(r"of\s+(\d+)",txt)
    total=int(m.group(1)) if m else 0
    tbl=soup.find(id="ctl00_ContentPlaceholder1_PortalPageControl1_ctl26_gvFileList")
    rows=[]; pages=set()
    if tbl:
        for tr in tbl.find_all("tr"):
            a=tr.find("a",id=re.compile("FileHyperLink$"))
            if not a: continue
            mm=re.search(r"Id=([0-9a-fA-F-]{36})",a.get("href",""))
            yr=tr.find("span",id=re.compile("lblYear$"))
            cat=tr.find("span",id=re.compile("lblCategory$"))
            rows.append({"desc":a.get_text(strip=True),
                         "doc_id":mm.group(1) if mm else "",
                         "year":yr.get_text(strip=True) if yr else "",
                         "category":cat.get_text(strip=True) if cat else ""})
        for a in tbl.find_all("a",href=re.compile(r"Page\$\d+")):
            pages.add(int(re.search(r"Page\$(\d+)",a["href"]).group(1)))
    return total, rows, sorted(pages)
