import fitz, os, json, io, time, sys
import pytesseract
from PIL import Image
from pathlib import Path
pytesseract.pytesseract.tesseract_cmd=r"C:\Users\esm247\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
RAW=str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "external" / "ancsa_portal")
OUT=str(Path(__file__).resolve().parent.parent.parent / "data" / "interim" / "ancsa_ocr")
scan=json.load(open(os.path.join(OUT,"text_scan.json")))
os.makedirs(os.path.join(OUT,"pages"),exist_ok=True)
# priority: fully blank docs first, then partial, biggest blank count first
def pri(x):
    if x.get("status")=="png": return (2,0)
    b=x.get("blank",0); p=x.get("pages",1) or 1
    return (0 if b==p else 1, -b)
todo=[x for x in scan if x.get("blank",0)>0]
todo.sort(key=pri)
log=open(os.path.join(OUT,"ocr_progress.log"),"a",encoding="utf-8")
def P(*a):
    s=" ".join(str(x) for x in a); print(s); log.write(s+"\n"); log.flush()
P("=== OCR START %s  files=%d pages=%d"%(time.strftime("%H:%M:%S"),len(todo),sum(x.get('blank',0) for x in todo)))
done_total=0
for x in todo:
    f=x["file"]; dst=os.path.join(OUT,"pages",f+".ocr.json")
    if os.path.exists(dst):
        P("skip(done)",f[:70]); continue
    p=os.path.join(RAW,f); res={}
    t0=time.time()
    try:
        if x.get("status")=="png":
            res["0"]=pytesseract.image_to_string(Image.open(p))
        else:
            d=fitz.open(p)
            for i in x["blank_pages"]:
                pg=d[i]
                pm=pg.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
                img=Image.open(io.BytesIO(pm.tobytes("png")))
                res[str(i)]=pytesseract.image_to_string(img)
            d.close()
    except Exception as e:
        P("ERR",f[:70],repr(e)[:120])
    json.dump(res,open(dst,"w",encoding="utf-8"))
    ch=sum(len(v) for v in res.values()); done_total+=len(res)
    P("ok %5.1fs pages=%3d chars=%7d  %s"%(time.time()-t0,len(res),ch,f[:80]))
P("=== OCR DONE %s pages=%d"%(time.strftime("%H:%M:%S"),done_total))
