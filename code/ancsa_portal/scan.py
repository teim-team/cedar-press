import fitz, os, re, json, sys, glob
from pathlib import Path
RAW=str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "external" / "ancsa_portal")
TXT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"txt")
os.makedirs(TXT,exist_ok=True)
KW=re.compile(r"(acquisit|acquired|acquire[sd]?\b|business combination|purchase price|"
              r"consideration transferred|goodwill|merger|merged|divestit|sold its|sale of "
              r"(?:its|the)|joint venture|equity method investment|purchased .{0,40}(?:stock|shares|assets|interest)|"
              r"stock purchase agreement|asset purchase agreement|letter of intent)",re.I)
def totext(p):
    out=os.path.join(TXT,os.path.basename(p)+".txt")
    if os.path.exists(out): return out
    try:
        d=fitz.open(p)
        t="\n".join("[[PAGE %d]]\n"%(i+1)+d[i].get_text() for i in range(d.page_count))
        d.close()
    except Exception as e:
        t="EXTRACT_ERROR "+repr(e)
    open(out,"w",encoding="utf-8").write(t)
    return out
if __name__=="__main__":
    pdfs=sorted(glob.glob(os.path.join(RAW,"*.pdf")))
    hits={}
    for p in pdfs:
        o=totext(p)
        t=open(o,encoding="utf-8").read()
        n=len(KW.findall(t))
        hits[os.path.basename(p)]={"chars":len(t),"kw":n}
        print("%5d kw  %8d chars  %s"%(n,len(t),os.path.basename(p)[:80]),flush=True)
    json.dump(hits,open("scan_hits.json","w"),indent=1)
