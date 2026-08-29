import requests, hashlib, os, csv, json, sys, time, re
RAW=r"C:\Users\esm247\Desktop\Cedar Press\data\raw\external\ancsa_portal"
os.makedirs(RAW,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
S=requests.Session(); S.headers.update({"User-Agent":UA})
S.get("https://portal.akdbsstar.us/StarWebPortal/page/default/portal.aspx",timeout=60)
def safe(s):
    s=re.sub(r'[^A-Za-z0-9._-]+','_',s).strip('_')
    return s[:110]
def fetch(doc_id, desc, subdir=""):
    url="https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="+doc_id
    d=os.path.join(RAW,subdir) if subdir else RAW
    os.makedirs(d,exist_ok=True)
    r=S.get(url,timeout=300)
    if r.status_code!=200 or not r.content: return None
    ct=r.headers.get("Content-Type","")
    ext=".pdf" if "pdf" in ct else (".mp4" if "video" in ct else ".bin")
    if r.content[:4]==b"%PDF": ext=".pdf"
    fn=safe(desc)+"__"+doc_id[:8]+ext
    p=os.path.join(d,fn)
    open(p,"wb").write(r.content)
    return {"local_file":(subdir+"/" if subdir else "")+fn,"bytes":len(r.content),
            "sha256":hashlib.sha256(r.content).hexdigest(),"content_type":ct,"url":url}
