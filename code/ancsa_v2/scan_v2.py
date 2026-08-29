import fitz,os,json,csv
RAW=r"C:\Users\esm247\Desktop\Cedar Press\data\raw\external\ancsa_portal_v2"
OUT=r"C:\Users\esm247\Desktop\Cedar Press\data\interim\ancsa_ocr_v2"
os.makedirs(OUT,exist_ok=True)
out=[]
for f in sorted(os.listdir(RAW)):
    if not f.lower().endswith(".pdf"): continue
    d=fitz.open(os.path.join(RAW,f)); bl=[i for i,p in enumerate(d) if len(p.get_text().strip())<100]
    if bl: out.append({"file":f,"status":"pdf","pages":d.page_count,"blank":len(bl),"blank_pages":bl})
    d.close()
json.dump(out,open(os.path.join(OUT,"text_scan.json"),"w"),indent=0)
print(len(out),"files",sum(x["blank"] for x in out),"pages")
