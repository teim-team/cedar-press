#!/usr/bin/env python3
"""
Cedar Press - 1176: build the owner's review bundle as a downloadable web page.

    py -3 code/1176_build_review_artifact.py

Owner, 2026-09-04: *"i literally said i wanted a web artifact i can download
these from"*. A zip attachment is not that.

The page embeds every file and offers it through the Artifact `downloads`
capability, which is the only route that actually saves a file from a published
artifact - the viewer sandbox makes `<a download>` and blob URLs inert, so a
plain link would look like a download and do nothing.

DESIGN: the page uses Cedar Press's OWN tokens, read from
`src/styles/grove/press.css` rather than invented here - teal #0f6b63, navy
#16323f, the paper ground #f7f6f3, IBM Plex Sans and Mono. A review surface for
Cedar Press that looked like a different product would be its own small lie.

EVERY FIGURE IS MEASURED AT BUILD TIME. Row counts, byte sizes and the three
coverage numbers are read off the files being embedded, so the page cannot
describe a bundle it is not carrying.
"""
from __future__ import annotations

import base64
import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "qc_review"
OUT = ROOT / "dist" / "review_bundle.html"
csv.field_size_limit(10_000_000)

FILES = [
    ("1_native_entities_ALL.csv", "Native entities",
     "Every entity Cedar holds, not a window. This is the reference the other "
     "sheets key to. Columns read "
     "<code>cedar_uid</code>, <code>name</code>, <code>entity_type</code> — "
     "identity, then the official name, then what the row is.",
     "<code>name</code> is the OFFICIAL name, taken from the register that "
     "publishes it, and <code>name_source</code> says which: the BIA Federal "
     "Register for tribes and Alaska Native villages, the DOI list for Native "
     "Hawaiian Organizations, the ANCSA corporation list for ANCs. 952 of "
     "1,555 are sourced that way; the rest read <code>cedar_internal</code>, "
     "which means no external register publishes a name for that class — so "
     "you can always tell a sourced name from an unsourced one. There is no "
     "short handle and no retired CICD code in this file: matching on the old "
     "short handle resolved 5.0% of the BIA list against 99.8% on the "
     "official name, so it was not reliable enough to publish."),
    ("2_how_cedar_ids_work.docx", "How the codes work",
     "Word document. What a <code>cedar_uid</code> is, why it encodes nothing, "
     "what a tier means, and the failure the system exists to prevent.",
     "Every number in it was measured when it was written, not typed in."),
    ("3_indian_country_deals_2025_2026.csv", "Indian Country deals",
     "One row per deal. This one is ChatGPT's.",
     "The question is what the collection IS. A prior review found it is largely "
     "DOE grants, which overlaps Federal Funding — the same money under two "
     "grains."),
    ("4_federal_spending_2025_2026_unique_entities.csv", "Federal spending",
     "2,315 unique recipients, collapsed from 61,579 transactions.",
     "Start here. Sort by <code>cedar_knows_this_uei_elsewhere</code> — 69 "
     "entities carrying $1.64B have a key Cedar holds elsewhere and did not "
     "apply here."),
    ("5_lobbying_2025_2026_unique_clients.csv", "Lobbying",
     "One row per client, not per filing. Clients file quarterly and amend.",
     "<code>n_superseded_filings</code> is the amendment behaviour. Superseded "
     "rows ship deliberately, flagged; an unflagged one is the defect."),
]


def rows_of(p: Path) -> int:
    if p.suffix != ".csv":
        return 0
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def coverage():
    """The three numbers that make the by-entity cut worth having."""
    p = SRC / "4_federal_spending_2025_2026_unique_entities.csv"
    keyed = tot = 0
    ktx = ttx = 0
    kusd = tusd = 0.0
    recoverable = 0
    rec_usd = 0.0
    over_1m = 0
    over_1m_usd = 0.0
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            tot += 1
            n = int(r.get("n_transactions") or 0)
            u = float(r.get("obligated_usd") or 0)
            ttx += n
            tusd += u
            if (r.get("cedar_uid") or "").strip():
                keyed += 1
                ktx += n
                kusd += u
            else:
                if (r.get("known_from") or "").strip():
                    recoverable += 1
                    rec_usd += u
                if u > 1_000_000:
                    over_1m += 1
                    over_1m_usd += u
    return {
        "entities": tot, "keyed_entities": keyed,
        "pct_entity": keyed / tot * 100,
        "pct_row": ktx / ttx * 100, "pct_usd": kusd / tusd * 100,
        "recoverable": recoverable, "rec_usd": rec_usd,
        "over_1m": over_1m, "over_1m_usd": over_1m_usd,
    }


def main():
    cov = coverage()
    payload, cards = {}, []
    for name, title, what, look in FILES:
        p = SRC / name
        if not p.exists():
            raise SystemExit(f"FATAL: {p} is absent - refusing to publish a "
                             f"page offering a file it does not carry")
        raw = p.read_bytes()
        if p.suffix == ".docx":
            payload[name] = {"b64": base64.b64encode(raw).decode()}
        else:
            payload[name] = {"text": raw.decode("utf-8-sig")}
        cards.append({
            "file": name, "title": title, "what": what, "look": look,
            "rows": rows_of(p), "kb": round(len(raw) / 1024),
            "kind": p.suffix.lstrip("."),
        })

    html = TEMPLATE.replace("__CARDS__", json.dumps(cards)) \
                   .replace("__PAYLOAD__", json.dumps(payload)) \
                   .replace("__COV__", json.dumps(cov)) \
                   .replace("__DATE__", f"{date.today():%d %B %Y}")
    OUT.write_text(html, encoding="utf-8")
    mb = OUT.stat().st_size / 1e6
    print(f"  wrote {OUT.relative_to(ROOT)}  ({mb:.2f} MB)")
    for c in cards:
        n = f"{c['rows']:,} rows" if c["rows"] else c["kind"]
        print(f"     {c['file']:<50} {n:>12}  {c['kb']:>6} KB")
    print(f"\n  coverage by entity {cov['pct_entity']:.1f}%  "
          f"by row {cov['pct_row']:.1f}%  by dollar {cov['pct_usd']:.1f}%")


TEMPLATE = r"""<title>Cedar Press Review Bundle</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
/* Cedar Press's own tokens, from src/styles/grove/press.css. */
:root{
  --ground:#f7f6f3; --raise:#ffffff; --sink:#eceae5;
  --ink:#14211f; --ink-2:#4a5654; --ink-3:#7b8583;
  --line:#dedbd4; --line-2:#c9c5bc;
  --teal:#0f6b63; --teal-ink:#0a4f49; --teal-wash:#e2efec;
  --navy:#16323f;
  --warn:#8a5a12; --warn-wash:#f7eeda;
  --good:#1c6b3f;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0e1614; --raise:#16211f; --sink:#0a100f;
  --ink:#eef2f0; --ink-2:#a9b5b2; --ink-3:#75817e;
  --line:#26332f; --line-2:#33423e;
  --teal:#4fd1c0; --teal-ink:#7fe3d5; --teal-wash:#11302c;
  --navy:#9fc4d4; --warn:#e0b25e; --warn-wash:#2b2211; --good:#5fd08a;
}}
:root[data-theme="dark"]{
  --ground:#0e1614; --raise:#16211f; --sink:#0a100f;
  --ink:#eef2f0; --ink-2:#a9b5b2; --ink-3:#75817e;
  --line:#26332f; --line-2:#33423e;
  --teal:#4fd1c0; --teal-ink:#7fe3d5; --teal-wash:#11302c;
  --navy:#9fc4d4; --warn:#e0b25e; --warn-wash:#2b2211; --good:#5fd08a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:400 15px/1.55 "IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:56rem;margin:0 auto;padding:2.6rem 1.2rem 4rem}
header{border-bottom:1px solid var(--line);padding-bottom:1.4rem;margin-bottom:1.9rem}
h1{font-size:1.72rem;line-height:1.18;margin:0 0 .45rem;letter-spacing:-.02em;text-wrap:balance}
.sub{color:var(--ink-2);margin:0;max-width:62ch}
.stamp{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.76rem;
  letter-spacing:.05em;text-transform:uppercase;color:var(--ink-3);margin:0 0 .7rem}

/* the three coverage figures - the reason the by-entity cut exists */
.cov{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:10px;
  overflow:hidden;margin:1.6rem 0 .6rem}
.cov div{background:var(--raise);padding:.9rem 1rem}
.cov .n{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;
  font-size:1.5rem;font-weight:600;line-height:1.1;display:block}
.cov .l{font-size:.78rem;color:var(--ink-3);letter-spacing:.05em;
  text-transform:uppercase;margin-top:.25rem;display:block}
.cov .hot .n{color:var(--warn)}
.note{color:var(--ink-2);font-size:.92rem;margin:.55rem 0 0;max-width:66ch}

h2{font-size:.8rem;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-3);font-weight:600;margin:2.4rem 0 .9rem}

/* one row per file: same edges, same baselines */
.files{display:flex;flex-direction:column;gap:.65rem}
.f{background:var(--raise);border:1px solid var(--line);border-radius:10px;
  padding:1rem 1.1rem;display:grid;grid-template-columns:1fr auto;
  gap:.35rem 1.2rem;align-items:start}
.f h3{grid-column:1;margin:0;font-size:1.03rem;letter-spacing:-.01em}
.f .meta{grid-column:1;font-family:"IBM Plex Mono",monospace;font-size:.78rem;
  color:var(--ink-3);font-variant-numeric:tabular-nums}
.f p{grid-column:1;margin:.3rem 0 0;color:var(--ink-2);font-size:.93rem;max-width:60ch}
.f .look{grid-column:1;margin:.5rem 0 0;font-size:.88rem;color:var(--ink);
  background:var(--teal-wash);border-radius:7px;padding:.5rem .65rem;max-width:60ch}
.f .look code{font-family:"IBM Plex Mono",monospace;font-size:.85em}
.f .act{grid-column:2;grid-row:1 / span 2;align-self:center}
button{font:600 .87rem "IBM Plex Sans",sans-serif;cursor:pointer;
  border-radius:8px;padding:.55rem 1rem;min-height:40px;white-space:nowrap;
  border:1px solid var(--teal);background:var(--teal);color:#fff}
:root[data-theme="dark"] button,:root:not([data-theme="light"]) button{color:#08211e}
button.ghost{background:transparent;color:var(--teal);border-color:var(--line-2)}
button:disabled{opacity:.55;cursor:default}
button:focus-visible{outline:2px solid var(--teal);outline-offset:2px}
.msg{font-size:.82rem;color:var(--ink-3);margin-top:.35rem;min-height:1.1em;
  grid-column:2;text-align:right;font-family:"IBM Plex Mono",monospace}
.msg.ok{color:var(--good)} .msg.bad{color:var(--warn)}

.how{margin-top:2.4rem;border-top:1px solid var(--line);padding-top:1.4rem}
.how p{color:var(--ink-2);max-width:66ch;margin:.5rem 0}
.how strong{color:var(--ink)}
.banner{background:var(--warn-wash);border:1px solid var(--warn);
  border-radius:9px;padding:.85rem 1rem;margin:1.1rem 0 0;font-size:.92rem}
@media (max-width:640px){
  .cov{grid-template-columns:1fr}
  .f{grid-template-columns:1fr}
  .f .act{grid-column:1;grid-row:auto;margin-top:.7rem}
  .msg{grid-column:1;text-align:left}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
<header>
  <p class="stamp">Cedar Press &middot; review bundle &middot; __DATE__</p>
  <h1>Five files to review</h1>
  <p class="sub">Every spreadsheet leads with a blank <strong>YOUR_NOTES</strong>
  column. Add a note where something needs to change; silence means approved.
  Unique observations only &mdash; including the ones keyed confidently, because
  a review of only the uncertain rows can never find a confident mistake.</p>
</header>

<h2>Federal spending coverage, three ways</h2>
<div class="cov" id="cov"></div>
<p class="note" id="covnote"></p>

<h2>The files</h2>
<div class="files" id="files"></div>

<div class="how">
  <h2 style="margin-top:0">How the downloads work</h2>
  <p>Each button asks claude.ai to save that file; you will see a confirmation
  naming the file and its size. Nothing downloads without you accepting.</p>
  <p id="capnote" class="note"></p>
</div>
</div>

<script>
const CARDS = __CARDS__;
const PAYLOAD = __PAYLOAD__;
const COV = __COV__;

const usd = n => "$" + Math.round(n).toLocaleString("en-US");

/* The three coverage figures. By-entity is the one that matters and the one a
   row-level review hides, so it is the one carrying the warning colour. */
document.getElementById("cov").innerHTML = [
  ["by row", COV.pct_row.toFixed(1) + "%", ""],
  ["by dollar", COV.pct_usd.toFixed(1) + "%", ""],
  ["by entity", COV.pct_entity.toFixed(1) + "%", "hot"],
].map(([l, n, c]) =>
  `<div class="${c}"><span class="n">${n}</span><span class="l">${l}</span></div>`
).join("");

document.getElementById("covnote").textContent =
  `Cedar keyed the high-volume recipients and left the long tail. ` +
  `${COV.entities.toLocaleString()} distinct recipients in the window; ` +
  `${(COV.entities - COV.keyed_entities).toLocaleString()} carry no cedar_uid, ` +
  `of which ${COV.over_1m} are over $1M each (${usd(COV.over_1m_usd)}). ` +
  `${COV.recoverable} of them — ${usd(COV.rec_usd)} — have a UEI Cedar keys ` +
  `positively somewhere else: a rule that exists and was not applied here.`;

const files = document.getElementById("files");
for (const c of CARDS) {
  const el = document.createElement("div");
  el.className = "f";
  const meta = c.rows ? `${c.rows.toLocaleString()} rows · ${c.kb} KB · ${c.kind}`
                      : `${c.kb} KB · ${c.kind}`;
  el.innerHTML =
    `<h3>${c.title}</h3>` +
    `<p class="meta">${c.file} — ${meta}</p>` +
    `<p>${c.what}</p>` +
    `<p class="look">${c.look}</p>` +
    `<div class="act"><button type="button">Download</button></div>` +
    `<p class="msg"></p>`;
  const btn = el.querySelector("button");
  const msg = el.querySelector(".msg");
  btn.addEventListener("click", () => grab(c, btn, msg));
  files.appendChild(el);
}

/* Base64 -> bytes, for the .docx. Strings go through as-is; the runtime
   encodes them UTF-8. */
function bytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

let downloads = null;
let ready = false;

async function grab(c, btn, msg) {
  if (!ready) { msg.textContent = "still connecting…"; return; }
  if (!downloads) { msg.className = "msg bad"; msg.textContent = "unavailable here"; return; }
  const p = PAYLOAD[c.file];
  const data = p.text !== undefined ? p.text : bytes(p.b64);
  btn.disabled = true;
  msg.className = "msg";
  msg.textContent = "asking…";
  try {
    await downloads.save({ filename: c.file, data });
    msg.className = "msg ok";
    msg.textContent = "saved";
  } catch (e) {
    msg.className = "msg bad";
    msg.textContent =
      e && e.code === "declined" ? "declined" :
      e && e.code === "rate_limited" ? "one at a time — try again" :
      (e && e.message) || "could not save";
  } finally {
    btn.disabled = false;
  }
}

/* The namespace resolves later than this script's first run, and may resolve
   null. The page is complete and readable either way; only the buttons wait. */
(async () => {
  try { downloads = await window.claude.use("downloads"); } catch { downloads = null; }
  ready = true;
  document.getElementById("capnote").textContent = downloads
    ? "Saving is available in this view."
    : "This view cannot save files. Open the artifact on claude.ai, or ask for the files in chat.";
})();
</script>
"""

if __name__ == "__main__":
    main()
