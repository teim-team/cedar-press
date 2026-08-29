#!/usr/bin/env python3
"""
Cedar Press - 68: Build the DECISIONS page.

Separate from the attribution review page, and deliberately so. That page is a
long grind through identifier cards. This one is two short jobs:

  1. SCOPE   - which open items matter and which do not. Several things are
               blocked or half-built that Elijah may simply not want, and me
               guessing wastes both our time.
  2. ENTITIES - 274 spine entities carry no identifier at all, so they are
               invisible in every dataset. Each needs one of: an identifier, a
               statement that it has no federal footprint, or removal.

Both export as CSV in the same format the pipeline already ingests.

Writes review/cedar_decisions_<date>_<n>.html
"""

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()


def out_path():
    n = 1
    while (REVIEW / f"cedar_decisions_{TODAY}_{n:02d}.html").exists():
        n += 1
    return REVIEW / f"cedar_decisions_{TODAY}_{n:02d}.html"


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


# Decided by Elijah 2026-08-06; dropped from the page rather than asked twice.
#   emma-licence / faads-pre2007 / sam-key   -> "doesn't matter, drop it"
#   contracts-2023 / dedupe-lib / entity-key-6 / gaming-dates /
#   gaming-semantics / six-month-hole        -> "matters, do it"
#   naming     CORRECTED: I read a stale branch. The floor is $1,000 not $500,
#              GitHub is actively updating, and HigherGov ships raw data with
#              no cleaning or insight - not the same product.
#   review-app / tbn-bundle                  -> he is handling both himself
SETTLED = {"emma-licence", "faads-pre2007", "sam-key", "naming",
           "review-app", "tbn-bundle", "contracts-2023", "dedupe-lib",
           "entity-key-6", "gaming-dates", "gaming-semantics",
           "six-month-hole"}

SCOPE = [
    ("gaming-dates", "Gaming: 215 facilities still undated",
     "Facility openings stop at 2018 in the inherited vendor column. Everything "
     "after that was dated by hand. 215 have no date at all.",
     "Gaming cannot be charted as a time series until this is filled.", "half-built"),
    ("gaming-semantics", "Gaming: open_date means two different things",
     "Some rows date when GAMING began, others when the PROPERTY opened. Crosby "
     "Lodge carries 1905-06-07 at 'exact' precision.",
     "Any 'tribal gaming since 19xx' series is wrong at the left tail and looks "
     "authoritative.", "half-built"),
    ("entity-key-6", "Compacts, bills, nonprofits, federal actions: 0% entity key",
     "Four datasets are built but carry no entity identifier, so they do not "
     "join to anything.",
     "Cross-dataset linkage - the actual product - is true of four datasets and "
     "false of six.", "half-built"),
    ("contracts-2023", "Prime contracting FY2023-2026 never pulled",
     "Script written and correctly refusing to start while the subaward puller "
     "holds the host.",
     "A launch dataset stops at FY2022.", "half-built"),
    ("six-month-hole", "2022-10-01 to 2023-04-04 is in no dataset",
     "The spine ends FY2022; the gapfill starts 2023-04-05. Half of FY2023 has "
     "never been pulled by anyone.",
     "A visible hole in a continuous series.", "half-built"),
    ("sam-key", "SAM.gov API key is dead",
     "Rotated 2026-07-25, returns 401 on v3 and v4. Harvest script written and "
     "ready. Would give self-declared Native business types with UEI + CAGE - "
     "an independent axis from our crosswalk.",
     "Blocks a large, cheap source of new UEIs and corroboration.", "blocked"),
    ("emma-licence", "Tribal debt: MSRB EMMA licensing",
     "EMMA's terms bar automated extraction AND bar building a database to be "
     "sold. Moody's redistribution is the same question.",
     "Blocks the tribal debt dataset entirely. A commercial decision, not a "
     "technical one.", "blocked"),
    ("faads-pre2007", "Federal assistance cannot attribute before FY2007",
     "0.0% of FY2001-2006 rows carry any recipient identifier, across all 11 "
     "agencies. Confirmed through two independent retrieval routes.",
     "Permanent. Programme-level totals only for those years.", "blocked"),
    ("naming", "Cedar Grove name and price collision",
     "Lumecon already sells Sprout $500 / Sapling $2,500 / Tree $7,500, and "
     "'Cedar Grove' is the $7,500 tier's data library. HigherGov sells at "
     "exactly $500 and $2,500.",
     "Both planned tiers collide on price and name.", "decision"),
    ("review-app", "Move the review page into the teim app",
     "Currently a static artifact with localStorage and CSV export. The "
     "claude/cedar-press branch has the landing page; the review queue is not "
     "in it.",
     "Every ruling is one copy-paste away from being lost.", "decision"),
    ("dedupe-lib", "Adopt active-learning record linkage (dedupe / splink)",
     "rapidfuzz and networkx are installed and unused. dedupe would learn from "
     "your rulings mechanically instead of me hand-writing each rule.",
     "Your notes would compound automatically.", "decision"),
    ("tbn-bundle", "Cedar Press bundled with Tribal Business News",
     "The mockup's gate reads 'Cedar Press comes with a Tribal Business News "
     "subscription.'",
     "If that is the distribution model it changes pricing and the TBN field.",
     "decision"),
]


def main():
    ent = read_csv(REVIEW / "unreconciled_entities.csv")
    print(f"unreconciled entities: {len(ent):,}")

    PRIORITY = {
        "Federally recognized tribe": 0,
        "Federally recognized Alaska Native Village": 1,
        "Alaska Native Village Corporation": 2,
        "ANCSA Group Corporation": 3,
        "Native Hawaiian Organization": 4,
        "Intertribal Organization": 5,
        "Federal-level constituency entity": 6,
        "State-recognized tribe": 6,
        "State-level constituency entity": 7,
    }
    WHY = {
        "Federally recognized tribe":
            "A federally recognised tribe with no identifier is almost "
            "certainly a linkage failure on our side, not an absence of "
            "federal activity. Highest priority.",
        "Federally recognized Alaska Native Village":
            "Village governments receive IHBG and BIA funding directly.",
        "Alaska Native Village Corporation":
            "Added to the spine today. The 19 already linked carry $23.9B; "
            "these are the same shape.",
        "ANCSA Group Corporation": "Smaller ANCSA corporations, same shape.",
        "Native Hawaiian Organization":
            "NHO contracting runs through 8(a) subsidiaries whose names rarely "
            "match the parent.",
        "Intertribal Organization":
            "Membership organisations. Many lobby and hold grants.",
        "Federal-level constituency entity":
            "Constituent bands. May have no separate identifier from the "
            "parent tribe - that is a legitimate answer.",
        "State-recognized tribe":
            "On the CICD roster, so the entity is real. State-recognised "
            "tribes DO appear in contracting and federal funding - a UEI or "
            "CAGE should be findable. Absence here is unfinished work.",
    }
    ent.sort(key=lambda r: (PRIORITY.get(r.get("entity_class", ""), 9),
                            r.get("canonical_name", "")))
    for r in ent:
        r["why"] = WHY.get(r.get("entity_class", ""), "")

    by = Counter(r.get("entity_class", "") for r in ent)
    scope_open = [{"id": i, "title": t, "detail": d, "impact": im, "kind": k}
                  for i, t, d, im, k in SCOPE if i not in SETTLED]
    print(f"scope items still open: {len(scope_open)} "
          f"({len(SCOPE) - len(scope_open)} already decided, dropped)")
    html = TEMPLATE.replace("__SCOPE__", json.dumps(scope_open)) \
        .replace("__ENTITIES__", json.dumps(ent)) \
        .replace("__DATE__", TODAY) \
        .replace("__NENT__", f"{len(ent):,}") \
        .replace("__NCLASS__", json.dumps(by.most_common()))
    p = out_path()
    p.write_text(html, encoding="utf-8")
    print(f"wrote {p.relative_to(CEDAR)}")


TEMPLATE = r"""<title>Cedar Press — Decisions</title>
<style>
:root{
  --ground:#F6F5F2; --panel:#FFFFFF; --edge:#E0DDD6;
  --ink:#1A1815; --ink-2:#57534C; --ink-3:#8A857C;
  --accent:#1F6F5C; --accent-soft:#E7F1ED;
  --stop:#A63D2F; --warn:#8A5A00; --ok:#1E6B37;
  --radius:10px;
}
@media (prefers-color-scheme:dark){
  :root{--ground:#14150F;--panel:#1D1F18;--edge:#33362B;
        --ink:#EDEBE4;--ink-2:#B4B0A6;--ink-3:#847F74;
        --accent:#5FBFA3;--accent-soft:#1B2C26;}
}
:root[data-theme="dark"]{--ground:#14150F;--panel:#1D1F18;--edge:#33362B;
  --ink:#EDEBE4;--ink-2:#B4B0A6;--ink-3:#847F74;--accent:#5FBFA3;--accent-soft:#1B2C26;}
:root[data-theme="light"]{--ground:#F6F5F2;--panel:#FFFFFF;--edge:#E0DDD6;
  --ink:#1A1815;--ink-2:#57534C;--ink-3:#8A857C;--accent:#1F6F5C;--accent-soft:#E7F1ED;}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:940px;margin:0 auto;padding:26px 18px 90px}
h1{font-size:25px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--ink-2);font-size:13px;margin-bottom:22px}
h2{font-size:17px;margin:34px 0 4px;letter-spacing:-.01em}
.h2sub{color:var(--ink-2);font-size:13px;margin-bottom:14px}
.card{background:var(--panel);border:1px solid var(--edge);border-radius:var(--radius);
  padding:13px 15px;margin-bottom:9px}
.card.done{opacity:.5}
.ttl{font-weight:600;margin-bottom:3px}
.det{color:var(--ink-2);font-size:13px;margin-bottom:5px}
.imp{color:var(--ink-3);font-size:12.5px;font-style:italic;margin-bottom:9px}
.tag{display:inline-block;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  padding:2px 7px;border-radius:99px;margin-right:7px;vertical-align:2px}
.t-blocked{background:#FBE9E7;color:var(--stop)}
.t-half{background:#FFF4E5;color:var(--warn)}
.t-decision{background:var(--accent-soft);color:var(--accent)}
@media (prefers-color-scheme:dark){.t-blocked{background:#3A1C18}.t-half{background:#3A2E12}}
.opts{display:flex;flex-wrap:wrap;gap:6px}
button.opt{font:inherit;font-size:13px;background:transparent;color:var(--ink);
  border:1px solid var(--edge);border-radius:99px;padding:5px 13px;cursor:pointer}
button.opt:hover{border-color:var(--accent)}
button.opt[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
input.idf,textarea.note{width:100%;font:inherit;font-size:13px;margin-top:7px;
  background:var(--ground);color:var(--ink);border:1px solid var(--edge);
  border-radius:7px;padding:7px 9px}
textarea.note{resize:vertical}
.meta{color:var(--ink-3);font-size:12px;margin-bottom:6px}
.why{color:var(--ink-3);font-size:12px;margin-bottom:8px;font-style:italic}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--panel);
  border-top:1px solid var(--edge);padding:9px 18px;display:flex;gap:10px;
  align-items:center;font-size:13px}
.bar .grow{flex:1;color:var(--ink-2)}
button.act{font:inherit;font-size:13px;background:var(--accent);color:#fff;border:0;
  border-radius:7px;padding:7px 15px;cursor:pointer}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--edge)}
#exp{display:none;margin-top:12px}
#exp[data-open="1"]{display:block}
textarea#csv{width:100%;height:230px;font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;
  background:var(--ground);color:var(--ink);border:1px solid var(--edge);
  border-radius:7px;padding:9px}
.grp{margin:20px 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-3);border-bottom:1px solid var(--edge);padding-bottom:5px}
.counts{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px}
.chip{font-size:12px;background:var(--panel);border:1px solid var(--edge);
  border-radius:99px;padding:3px 10px;color:var(--ink-2)}
</style>

<div class="wrap">
<h1>Cedar Press — Decisions</h1>
<div class="sub">__DATE__ · two jobs: say what matters, then reconcile the entities that link to nothing. Saves as you go.</div>

<h2>1 · Does this matter?</h2>
<div class="h2sub">Open items. Several may simply not be things you want — say so and they stop taking up room.</div>
<div id="scope"></div>

<h2>2 · Entities that link to nothing</h2>
<div class="h2sub">__NENT__ spine entities carry no UEI, CAGE or EIN, so they are invisible in every dataset. Give an identifier, or say it has no federal footprint.</div>
<div class="counts" id="counts"></div>
<div id="ents"></div>

<div id="exp"><textarea id="csv" readonly spellcheck="false"></textarea></div>
</div>

<div class="bar">
  <span class="grow" id="status">nothing decided yet</span>
  <button class="act ghost" id="close" style="display:none">close</button>
  <button class="act" id="export">Export decisions</button>
</div>

<script>
const SCOPE=__SCOPE__, ENTS=__ENTITIES__, CLASSES=__NCLASS__;
const KEY="cedar_decisions_v1";
let D={};
try{D=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){D={}}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(D))}catch(e){}};
const el=(t,c)=>{const n=document.createElement(t);if(c)n.className=c;return n};

function status(){
  const n=Object.keys(D).length;
  document.getElementById("status").textContent =
    n? n+" decided · "+(SCOPE.length+ENTS.length-n)+" left" : "nothing decided yet";
}

/* ---- scope ---- */
const KIND={blocked:["t-blocked","blocked"],"half-built":["t-half","half built"],
            decision:["t-decision","your call"]};
const sc=document.getElementById("scope");
SCOPE.forEach(it=>{
  const c=el("div","card");
  const k=KIND[it.kind]||KIND.decision;
  const t=el("span","tag "+k[0]); t.textContent=k[1];
  const h=el("div","ttl"); h.appendChild(t); h.appendChild(document.createTextNode(it.title));
  c.appendChild(h);
  const d=el("div","det"); d.textContent=it.detail; c.appendChild(d);
  const i=el("div","imp"); i.textContent=it.impact; c.appendChild(i);
  const o=el("div","opts");
  ["Matters — do it","Later","Doesn't matter — drop it"].forEach(lbl=>{
    const b=el("button","opt"); b.type="button"; b.textContent=lbl;
    b.setAttribute("aria-pressed", D[it.id]&&D[it.id].v===lbl ? "true":"false");
    b.onclick=()=>{
      D[it.id]={kind:"scope",label:it.title,v:lbl,note:(D[it.id]||{}).note||""};
      save(); o.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
      b.setAttribute("aria-pressed","true"); c.classList.add("done"); status();
    };
    o.appendChild(b);
  });
  c.appendChild(o);
  const n=el("textarea","note"); n.rows=1; n.placeholder="why / any context";
  n.value=(D[it.id]||{}).note||"";
  n.oninput=()=>{D[it.id]=D[it.id]||{kind:"scope",label:it.title,v:""};
    D[it.id].note=n.value; save();};
  c.appendChild(n);
  if(D[it.id]&&D[it.id].v) c.classList.add("done");
  sc.appendChild(c);
});

/* ---- counts ---- */
const cn=document.getElementById("counts");
CLASSES.forEach(([k,v])=>{const s=el("span","chip");s.textContent=v+" "+k;cn.appendChild(s)});

/* ---- entities ---- */
const ec=document.getElementById("ents");
let last=null;
ENTS.forEach(e=>{
  if(e.entity_class!==last){
    last=e.entity_class;
    const g=el("div","grp"); g.textContent=e.entity_class; ec.appendChild(g);
    if(e.why){const w=el("div","why"); w.textContent=e.why; ec.appendChild(w);}
  }
  const id="ENT:"+e.tribe_id;
  const c=el("div","card");
  const h=el("div","ttl"); h.textContent=e.canonical_name; c.appendChild(h);
  const m=el("div","meta");
  m.textContent=e.tribe_id+(e.state?"  ·  "+e.state:"")+
    (e.ultimate_parent_entity_name&&e.ultimate_parent_entity_name!==e.canonical_name
      ? "  ·  rolls up to "+e.ultimate_parent_entity_name : "");
  c.appendChild(m);
  const o=el("div","opts");
  ["Has federal activity — find it","No federal footprint","Not a real entity — remove","Duplicate of another row"]
   .forEach(lbl=>{
    const b=el("button","opt"); b.type="button"; b.textContent=lbl;
    b.setAttribute("aria-pressed", D[id]&&D[id].v===lbl ? "true":"false");
    b.onclick=()=>{
      D[id]=Object.assign({kind:"entity",label:e.canonical_name,tribe_id:e.tribe_id},
                          D[id]||{},{v:lbl});
      save(); o.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
      b.setAttribute("aria-pressed","true"); c.classList.add("done"); status();
    };
    o.appendChild(b);
  });
  c.appendChild(o);
  const f=el("input","idf"); f.type="text";
  f.placeholder="UEI / CAGE / EIN if you know it — or the name it actually files under";
  f.value=(D[id]||{}).ident||"";
  f.oninput=()=>{D[id]=Object.assign({kind:"entity",label:e.canonical_name,
    tribe_id:e.tribe_id,v:""},D[id]||{}); D[id].ident=f.value; save();};
  c.appendChild(f);
  if(D[id]&&D[id].v) c.classList.add("done");
  ec.appendChild(c);
});

/* ---- export ---- */
const box=document.getElementById("exp"), ta=document.getElementById("csv"),
      cl=document.getElementById("close");
document.getElementById("export").onclick=()=>{
  const q=s=>'"'+String(s==null?"":s).replace(/"/g,'""')+'"';
  const rows=[["decision_id","kind","label","tribe_id","YOUR_DECISION","identifier","note"].join(",")];
  Object.keys(D).sort().forEach(k=>{const d=D[k];
    rows.push([k,d.kind||"",d.label||"",d.tribe_id||"",d.v||"",d.ident||"",d.note||""].map(q).join(","));});
  ta.value=rows.join("\n"); box.dataset.open="1"; cl.style.display="";
  ta.focus(); ta.select();
};
cl.onclick=()=>{box.dataset.open="0"; cl.style.display="none";};
status();
</script>
"""


if __name__ == "__main__":
    main()
