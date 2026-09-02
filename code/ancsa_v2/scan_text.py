import fitz, os, json, csv, sys
from pathlib import Path
RAW=str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "external" / "ancsa_portal")
man=list(csv.DictReader(open(os.path.join(RAW,"_SOURCE_MANIFEST.csv"),newline="",encoding="utf-8-sig")))
out=[]
for r in man:
    f=r["local_file"]; p=os.path.join(RAW,f)
    if not os.path.exists(p): out.append({"file":f,"status":"MISSING"}); continue
    if f.lower().endswith(".png"):
        out.append({"file":f,"corp":r["corporation"],"year":r["period_covered"],"status":"png","pages":1,"blank":1,"chars":0}); continue
    try:
        d=fitz.open(p)
    except Exception as e:
        out.append({"file":f,"status":"ERR "+str(e)}); continue
    blanks=[]; tot=0
    for i,pg in enumerate(d):
        t=pg.get_text().strip(); tot+=len(t)
        if len(t)<100: blanks.append(i)
    out.append({"file":f,"corp":r["corporation"],"year":r["period_covered"],"status":"pdf",
                "pages":d.page_count,"blank":len(blanks),"chars":tot,"blank_pages":blanks})
    d.close()
json.dump(out,open(str(Path(__file__).resolve().parent.parent.parent / "data" / "interim" / "ancsa_ocr" / "text_scan.json"),"w"),indent=0)
tb=sum(x.get("blank",0) for x in out)
print("files",len(out),"total blank pages",tb)
for x in sorted(out,key=lambda z:-z.get("blank",0))[:45]:
    print(x.get("blank"),"/",x.get("pages"),x.get("chars"),x["file"][:95])
