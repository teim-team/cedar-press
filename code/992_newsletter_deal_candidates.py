"""Deals, mined out of the tribal press.

Owner: *"Don't forget tribal newsletters, especially for deals."* He is right
about the mechanism. A nation's own newspaper reports the joint venture, the
acquisition and the new subsidiary in the nation's own words, and it does so
before any federal filing exists - often before there is anything to file.
`deals` is the one Cedar product nobody else has, and this is the route that
feeds it something no federal source can.

WHAT THIS DOES
  1. Takes the issue and article URLs already indexed by
     `990_build_newsletter_corpus.py` (`recent_issue_urls`) and by
     `991_newsletter_gap_sweep.py`.
  2. Fetches each once, hashes it, and refuses to trust a host that returns the
     same body for different URLs.
  3. Extracts sentences that state a TRANSACTION, not sentences that merely
     contain a business word.
  4. Screens every candidate against the private-life filter before it is
     written anywhere.
  5. Screens every candidate against the intra-family rule.
  6. Stages the survivors. It does NOT edit `deals_classified.csv`.

THE TWO SCREENS, BOTH OF WHICH MATTER MORE THAN RECALL

*Private life.* A tribal newsletter is a community newspaper. It carries
obituaries, birthdays, funeral notices, health bulletins and family news about
private individuals who are not public figures. Cedar harvests the
PUBLICATION; it does not extract a natural person's private news from it. Any
candidate whose surrounding text is personal is dropped and counted, never
written to a staged row.

*Intra-family reparenting.* The owner: *"some wonky stuff where a company
changes from All Native Group to Ho-Chunk Inc, but it's still the same Native
entity."* A subsidiary moving between two arms of one tribal corporate family
is a reporting change, not a transaction, and counting it inflates deal volume
with motion that never happened. Candidates whose two parties resolve to the
same ultimate parent are written with
`intra_family_reporting_change = yes` and `deal_status_std = NOT_A_TRANSACTION`
so they are visible and excluded from every total.

STATUS. `Announced` and `Closed` are labelled separately from the verb the
publication actually used, and the verb is kept in `status_basis`. A candidate
whose status cannot be read from the text is `UNCLASSIFIED`, never assumed
closed. Nothing here carries a value unless the text states one.

OUTPUT - staged, not merged. Another agent owns `deals` promotion.
    data/staging/deals_from_newsletters/deal_candidates.csv
    data/staging/deals_from_newsletters/_documents.jsonl   (fetch ledger)

    python code/992_newsletter_deal_candidates.py                # resumable
    python code/992_newsletter_deal_candidates.py --limit 40
    python code/992_newsletter_deal_candidates.py verify
    python code/992_newsletter_deal_candidates.py verify --selftest
"""
from __future__ import annotations

import csv
import hashlib
import html as htmlmod
import io
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "clean" / "tribal_newsletter_corpus.csv"
SWEEP = (ROOT / "data" / "staging" / "tribe_harvest" / "newsletter_gap_sweep"
         / "gap_sweep.jsonl")
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
OUTD = ROOT / "data" / "staging" / "deals_from_newsletters"
OUT = OUTD / "deal_candidates.csv"
LEDGER = OUTD / "_documents.jsonl"
STATE = OUTD / "_state.json"
OUTD.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

UA = ("CedarPress-research/1.0 (tribal newsletter corpus; "
      "contact elijahsamsonmoreno@gmail.com)")
HOST_DELAY = 1.8
RUN_DEADLINE = time.time() + 3 * 3600
MAX_DOC_BYTES = 45_000_000

RESTRICTIVE_HOSTS = {
    "colvilletribes.com", "tribaltribune.com", "colvillecasinos.com",
    "ctuir.org", "wildhorseresort.com",
    "yakama.com", "yakama.org", "legendscasino.com",
    "chickasaw.net", "chickasawtimes.net", "chickasawbusinessnetwork.com",
    "nana.com", "akima.com",
    "southernute-nsn.gov", "sudrum.com", "skyutecasino.com",
    "fcpotawatomi.com", "potawatomi.com", "paysbig.com", "cartercasino.com",
    "stillaguamish.com", "angelofthewinds.com",
}
RESTRICTIVE_UIDS = {"CE-0013K-5M", "CE-001BT-Q3", "CE-001CC-8N", "CE-00135-HP",
                    "CE-0007G-30", "CE-001AX-4Y", "CE-0014H-YJ", "CE-001AY-AQ"}

# --- a transaction needs an ACTION. "our business partners" is not a deal.
DEAL = re.compile(
    r"(?i)\b("
    r"acquir(?:e|es|ed|ing)|acquisition of|"
    r"has purchased|have purchased|purchased (?:the|all|a majority|100)|"
    r"merger with|merged with|merge with|"
    r"joint venture (?:with|between|agreement)|"
    r"formed a (?:joint venture|partnership|new company|new subsidiary)|"
    r"(?:new|wholly[- ]owned|majority[- ]owned) subsidiary|"
    r"majority (?:interest|stake|ownership) in|"
    r"controlling interest in|"
    r"divest(?:s|ed|iture)?(?: of)?|sold (?:its|their|the) (?:interest|stake|share)|"
    r"(?:signed|entered into) (?:a |an )?(?:definitive )?"
    r"(?:agreement|memorandum of understanding|letter of intent)|"
    r"awarded a (?:\$[\d.,]+ ?(?:million|billion)? )?(?:contract|task order|"
    r"prime contract|subcontract)|"
    r"was awarded (?:a|an|the)|"
    r"closed on (?:the|a|its)|"
    r"broke ground on|groundbreaking (?:for|on)|"
    r"issued (?:\$[\d.,]+ ?(?:million|billion)? (?:in )?)?(?:bonds|notes)|"
    r"refinanc(?:e|ed|ing) of|"
    r"completed the (?:acquisition|purchase|sale|merger)"
    r")\b")

# "$151B" is one hundred fifty-one BILLION dollars, and the first version of
# this pattern read it as $151 because the alternation carried `bn` and
# `billion` but not a bare `b`. A 10^9 error on a contract ceiling is the kind
# of number a customer notices.
MONEY = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*"
    r"(billion|bn\b|b\b|million|mm\b|m\b|thousand|k\b)?", re.I)

CLOSED = re.compile(
    r"(?i)\b(completed|closed on|has acquired|have acquired|acquired|"
    r"finaliz\w+|was awarded|has been awarded|purchased|took ownership|"
    r"now a wholly[- ]owned|became a subsidiary)\b")
ANNOUNCED = re.compile(
    r"(?i)\b(announc\w+|plans to|intends to|will acquire|has agreed to|"
    r"entered into a definitive|signed a letter of intent|proposed|"
    r"expects to close|pending)\b")

# --- the private-life screen. Anything near this vocabulary is community news
# about a person, and Cedar does not extract it.
PRIVATE = re.compile(
    r"(?i)\b(obituar\w+|in memoriam|passed away|passing of|funeral|memorial "
    r"service|survived by|celebration of life|born to|birth announcement|"
    r"birthday|happy birthday|anniversary of their|wedding|engaged to|"
    r"graduat\w+ from high school|honor roll|diagnos\w+|hospice|"
    r"in loving memory|condolences|pallbearer|visitation will|"
    r"is recovering|health update|prayers for)\b")

DATEPAT = re.compile(
    r"(?i)\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+(20\d\d)\b")

FIELDS = [
    "candidate_id", "cedar_uid", "tribe_id", "Native_Party",
    "native_party_entity_class", "State", "Counterparty_or_Funder",
    "Event_Date", "Event_Year", "date_basis", "Event_Type",
    "Status", "deal_status_std", "status_basis",
    "Announced_Value_USD", "value_basis",
    "Description", "matched_phrase",
    "intra_family_reporting_change", "intra_family_basis",
    "Source_1", "Source_1_Type", "source_publication", "source_channel_url",
    "document_md5", "retrieved_date", "Confidence", "review_status", "Notes",
]

_last = {}


def sleep_host(h):
    t = _last.get(h)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[h] = time.time()


def restricted(uid, url):
    if uid in RESTRICTIVE_UIDS:
        return True
    h = urlparse(url or "").netloc.lower().lstrip("www.")
    return bool(h) and any(h == d or h.endswith("." + d) for d in RESTRICTIVE_HOSTS)


def get(url, timeout=45):
    h = urlparse(url).netloc.lower()
    sleep_host(h)
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "--max-time", str(timeout), "--max-filesize", str(MAX_DOC_BYTES),
           "-w", "\n__HTTPSTATUS__%{http_code}__CT__%{content_type}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 25)
    except subprocess.TimeoutExpired:
        return 0, "", b""
    out = p.stdout
    m = re.search(rb"\n__HTTPSTATUS__(\d+)__CT__(.*)$", out, re.S)
    status = int(m.group(1)) if m else 0
    ct = m.group(2).decode("latin-1", "replace").strip() if m else ""
    body = out[: m.start()] if m else out
    return status, ct, body


def to_text(body, ct, url):
    if b"%PDF" == body[:4] or "pdf" in ct.lower() or url.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            rd = PdfReader(io.BytesIO(body))
            pages = [(p.extract_text() or "") for p in rd.pages[:40]]
            return "\n".join(pages), "pdf", len(rd.pages)
        except Exception:                                        # noqa: BLE001
            return "", "pdf_unreadable", 0
    t = body.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|nav|footer|header)\b.*?</\1>", " ", t)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|tr|h\d)>", "\n", t)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return "\n".join(ln.strip() for ln in t.split("\n") if ln.strip()), "html", 0


def sentences(text):
    for para in text.split("\n"):
        para = para.strip()
        if len(para) < 40:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", para):
            s = s.strip()
            if 40 <= len(s) <= 700:
                yield s


def money_usd(s):
    m = MONEY.search(s)
    if not m:
        return "", ""
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return "", ""
    mult = {"billion": 1e9, "bn": 1e9, "b": 1e9,
            "million": 1e6, "mm": 1e6, "m": 1e6,
            "thousand": 1e3, "k": 1e3}.get((m.group(2) or "").lower().strip(), 1.0)
    return "%.0f" % (n * mult), "stated in the source sentence: %s" % m.group(0)


def load_families():
    """ultimate-parent map, for the intra-family screen."""
    fam, names = {}, {}
    for r in csv.DictReader(SPINE.open(encoding="utf-8-sig")):
        top = (r.get("ultimate_parent_entity_name") or r.get("parent_entity_name")
               or r.get("canonical_name") or "").strip().lower()
        nm = (r.get("canonical_name") or "").strip()
        if nm:
            fam[nm.lower()] = top or nm.lower()
            names[nm.lower()] = r["cedar_uid"]
        for a in (r.get("aliases") or "").split(";"):
            a = a.strip().lower()
            if len(a) > 4:
                fam.setdefault(a, top or nm.lower())
                names.setdefault(a, r["cedar_uid"])
    return fam, names


ORG = re.compile(
    r"\b([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,5}\s+"
    r"(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|Corporation|Corp\.?|Company|Co\.|"
    r"Group|Holdings|Enterprises|Ventures|Partners|Technologies|Solutions|"
    r"Services|Development Authority|Development Corporation))\b")


def parties(sent, publisher):
    orgs = [m.group(1).strip() for m in ORG.finditer(sent)]
    orgs = [o for o in orgs if o.lower() != publisher.lower()][:4]
    return orgs


def intra_family(publisher, counterparties, fam):
    """The Ho-Chunk / All Native Group rule."""
    p = fam.get(publisher.lower())
    for c in counterparties:
        c_root = fam.get(c.lower())
        if c_root and p and c_root == p:
            return "yes", ("both parties resolve to the same ultimate parent "
                           "(%s); a change of reporting parent inside one tribal "
                           "corporate family is NOT a transaction" % p)
    return "no", ""


def targets():
    """(cedar_uid, tribe_id, publisher, class, state, publication, channel, url)"""
    seen, out = set(), []
    for r in csv.DictReader(CORPUS.open(encoding="utf-8-sig")):
        if restricted(r["cedar_uid"], r["channel_url"]):
            continue
        # deal content lives in issues, and the channels most likely to carry it
        # are the ones whose index already showed business vocabulary. Order by
        # that, but do not exclude on it - the index is a weak signal.
        for u in r["recent_issue_urls"].split(" | "):
            u = u.strip()
            if not u.startswith("http") or u in seen:
                continue
            if restricted(r["cedar_uid"], u):
                continue
            if urlparse(u).netloc.lower().endswith("archive.org"):
                continue
            seen.add(u)
            out.append({
                "cedar_uid": r["cedar_uid"], "tribe_id": r["tribe_id"],
                "publisher": r["publisher_name"], "entity_class": r["entity_class"],
                "state": r["state"], "publication": r["publication_name"],
                "channel_url": r["channel_url"], "url": u,
                "priority": 0 if r["business_content"] == "yes" else 1,
            })
    if SWEEP.exists():
        for line in SWEEP.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if restricted(d["cedar_uid"], d.get("site", "")):
                continue
            for f in d.get("found") or []:
                if f["kind"] != "issue_pdf":
                    continue
                u = f["url"]
                if u in seen or restricted(d["cedar_uid"], u):
                    continue
                seen.add(u)
                out.append({
                    "cedar_uid": d["cedar_uid"], "tribe_id": d["tribe_id"],
                    "publisher": d["canonical_name"],
                    "entity_class": d["entity_class"], "state": d["state"],
                    "publication": f.get("title", ""), "channel_url": d["site"],
                    "url": u, "priority": 0,
                })
    out.sort(key=lambda x: (x["priority"], x["publisher"].lower()))
    return out


def mine(doc_text, t, fam, md5):
    rows, dropped_private = [], 0
    pub = t["publisher"]
    # An occurrence counter, because a PDF that prints the same sentence in a
    # summary box and again in the body produced two rows with one id. The key
    # has to be unique on its own terms; "it is almost always unique" is how a
    # primary key stops being one.
    seen_sent = Counter()
    for s in sentences(doc_text):
        m = DEAL.search(s)
        if not m:
            continue
        # PRIVATE-LIFE SCREEN, applied to the sentence AND to its neighbourhood
        i = doc_text.find(s)
        window = doc_text[max(0, i - 400): i + len(s) + 400] if i >= 0 else s
        if PRIVATE.search(s) or PRIVATE.search(window):
            dropped_private += 1
            continue
        cps = parties(s, pub)
        fam_flag, fam_basis = intra_family(pub, cps, fam)
        val, vbasis = money_usd(s)
        if CLOSED.search(s):
            std, status, sbasis = "Closed", "Closed", "past-tense completion verb in the source sentence"
        elif ANNOUNCED.search(s):
            std, status, sbasis = "Announced", "Announced", "announcement or forward-looking verb in the source sentence"
        else:
            std, status, sbasis = "UNCLASSIFIED", "", "no status verb in the source sentence; not assumed"
        if fam_flag == "yes":
            std = "NOT_A_TRANSACTION"
        dm = DATEPAT.search(window)
        rows.append({
            "candidate_id": "NLDEAL-%s%s" % (
                hashlib.md5((t["url"] + "|" + s[:160]).encode("utf-8")).hexdigest()[:12],
                "" if seen_sent[s[:160]] == 0 else "-%d" % (seen_sent[s[:160]] + 1)),
            "cedar_uid": t["cedar_uid"], "tribe_id": t["tribe_id"],
            "Native_Party": pub,
            "native_party_entity_class": t["entity_class"], "State": t["state"],
            "Counterparty_or_Funder": "; ".join(cps),
            "Event_Date": "", "Event_Year": dm.group(2) if dm else "",
            "date_basis": ("year read from a date printed near the sentence"
                           if dm else "no date in the source text"),
            "Event_Type": m.group(1).strip().lower(),
            "Status": status, "deal_status_std": std, "status_basis": sbasis,
            "Announced_Value_USD": val, "value_basis": vbasis,
            "Description": re.sub(r"\s+", " ", s)[:600],
            "matched_phrase": m.group(1).strip(),
            "intra_family_reporting_change": fam_flag,
            "intra_family_basis": fam_basis,
            "Source_1": t["url"], "Source_1_Type": "Tribal newsletter / tribal press",
            "source_publication": t["publication"],
            "source_channel_url": t["channel_url"],
            "document_md5": md5, "retrieved_date": TODAY,
            "Confidence": "candidate - pattern match on publisher's own text, "
                          "NOT hand-verified",
            "review_status": "UNREVIEWED",
            "Notes": "staged by code/992_newsletter_deal_candidates.py; not "
                     "merged into deals_classified.csv",
        })
        seen_sent[s[:160]] += 1
    return rows, dropped_private


def run(limit=None):
    fam, _names = load_families()
    tg = targets()
    done, doc_hashes = set(), Counter()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                done.add(d["url"])
                if d.get("md5"):
                    doc_hashes[(d["host"], d["md5"])] += 1
    todo = [t for t in tg if t["url"] not in done]
    if limit:
        todo = todo[:limit]
    print("documents indexed %d; already fetched %d; this run %d"
          % (len(tg), len(done), len(todo)), file=sys.stderr)

    new = not OUT.exists()
    fout = OUT.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(fout, fieldnames=FIELDS, extrasaction="ignore")
    if new:
        w.writeheader()
        fout.flush()
    flog = LEDGER.open("a", encoding="utf-8")

    n_rows = 0
    for i, t in enumerate(todo):
        if time.time() > RUN_DEADLINE:
            print("RUN_DEADLINE reached", file=sys.stderr)
            break
        host = urlparse(t["url"]).netloc.lower()
        status, ct, body = get(t["url"])
        md5 = hashlib.md5(body).hexdigest() if body else ""
        entry = {"url": t["url"], "host": host, "cedar_uid": t["cedar_uid"],
                 "http_status": status, "content_type": ct, "bytes": len(body),
                 "md5": md5, "fetched_date": TODAY, "chars": 0, "kind": "",
                 "candidates": 0, "dropped_private": 0, "note": ""}
        if status == 200 and body:
            doc_hashes[(host, md5)] += 1
            # the ?wpdmdl= trap: one host, one body, many URLs
            if doc_hashes[(host, md5)] >= 3:
                entry["note"] = ("IDENTICAL_BODY_REPEAT: this host has now "
                                 "returned this exact body for %d different "
                                 "URLs; document not mined"
                                 % doc_hashes[(host, md5)])
            else:
                text, kind, _pg = to_text(body, ct, t["url"])
                entry["chars"], entry["kind"] = len(text), kind
                if text:
                    rows, dp = mine(text, t, fam, md5)
                    entry["candidates"], entry["dropped_private"] = len(rows), dp
                    for r in rows:
                        w.writerow(r)
                    fout.flush()
                    n_rows += len(rows)
                else:
                    entry["note"] = "no extractable text (image-only PDF or empty body)"
        elif status == 200 and not body:
            # curl reports 200 and hands back nothing when --max-filesize trips
            # or the transfer aborts. Recording that as a plain "http 200" would
            # file a fetch failure as a success, which is the same lie as a 200
            # with the wrong content.
            entry["note"] = ("http 200 but EMPTY body - transfer aborted or over "
                             "the %d-byte cap; counted as a FAILURE, not a "
                             "document" % MAX_DOC_BYTES)
        else:
            entry["note"] = "http %s" % status
        flog.write(json.dumps(entry, ensure_ascii=False) + "\n")
        flog.flush()
        if (i + 1) % 25 == 0:
            print("  %d/%d  rows so far %d" % (i + 1, len(todo), n_rows),
                  file=sys.stderr)
    fout.close()
    flog.close()
    st = summarize()
    print(json.dumps(st, indent=2)[:3500])
    return 0


def summarize():
    rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig"))) if OUT.exists() else []
    docs = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines()
            if l.strip()] if LEDGER.exists() else []
    tg = targets()
    real = [r for r in rows if r["deal_status_std"] != "NOT_A_TRANSACTION"]
    st = {
        "script": "code/992_newsletter_deal_candidates.py", "run_date": TODAY,
        "documents_indexed": len(tg), "documents_fetched": len(docs),
        "run_complete": len({d["url"] for d in docs}) >= len(tg),
        "documents_http_200": sum(1 for d in docs if d["http_status"] == 200),
        "documents_with_text": sum(1 for d in docs if d.get("chars")),
        "distinct_document_md5": len({d["md5"] for d in docs if d.get("md5")}),
        "identical_body_repeats_blocked": sum(
            1 for d in docs if "IDENTICAL_BODY_REPEAT" in (d.get("note") or "")),
        "candidates": len(rows),
        "candidates_excluded_intra_family": len(rows) - len(real),
        "sentences_dropped_private_life": sum(d.get("dropped_private", 0) for d in docs),
        "by_status": dict(Counter(r["deal_status_std"] for r in rows)),
        "by_event_type": dict(Counter(r["Event_Type"] for r in real).most_common(20)),
        "with_a_stated_value": sum(1 for r in real if r["Announced_Value_USD"]),
        "distinct_native_parties": len({r["Native_Party"] for r in real}),
        "top_parties": dict(Counter(r["Native_Party"] for r in real).most_common(15)),
    }
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st


def refresh_values(paths=None):
    """Re-derive Announced_Value_USD from the stored source sentence.

    Legitimate because `Description` IS the source sentence, verbatim: this
    re-reads what was already captured rather than asserting anything new. Run
    it after any fix to MONEY - which is how "$151B" stopped being a hundred
    and fifty-one dollars.
    """
    from pathlib import Path as _P
    paths = paths or [OUT, OUTD / "deal_candidates_wp_posts.csv",
                      OUTD / "deal_candidates_wp_posts_quarantined.csv"]
    for p in paths:
        p = _P(p)
        if not p.exists():
            continue
        rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
        if not rows:
            continue
        fn = list(rows[0].keys())
        changed = 0
        for r in rows:
            val, basis = money_usd(r["Description"])
            if val != r.get("Announced_Value_USD", ""):
                changed += 1
            r["Announced_Value_USD"], r["value_basis"] = val, basis
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
                f.flush()
        print("refresh_values %s: %d changed" % (p.name, changed))
    return 0


def repair_ids(paths=None):
    """Make candidate_id unique in files written before the counter existed.

    A rename, not a deletion: the collided rows are distinct sentences-in-place
    and both stay. Suffixes are assigned in file order so the repair is
    deterministic and re-running it is a no-op.
    """
    from pathlib import Path as _P
    paths = paths or [OUT, OUTD / "deal_candidates_wp_posts.csv"]
    total = 0
    for p in paths:
        p = _P(p)
        if not p.exists():
            continue
        rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
        if not rows:
            continue
        fn = list(rows[0].keys())
        seen, fixed = Counter(), 0
        for r in rows:
            base = re.sub(r"-\d+$", "", r["candidate_id"])
            seen[base] += 1
            if seen[base] > 1:
                r["candidate_id"] = "%s-%d" % (base, seen[base])
                fixed += 1
            else:
                r["candidate_id"] = base
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
                f.flush()
        print("repair_ids %s: %d renamed" % (p.name, fixed))
        total += fixed
    return 0


# ------------------------------------------------------------------ verify
def verify(rows=None, docs=None):
    if rows is None:
        rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig"))) if OUT.exists() else []
    if docs is None:
        docs = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines()
                if l.strip()] if LEDGER.exists() else []
    f = []

    # 1. no restricted publisher, by uid or by source host
    bad = [r for r in rows if restricted(r["cedar_uid"], r["Source_1"])]
    if bad:
        f.append("RESTRICTIVE_SOURCE_PRESENT: %d, e.g. %s" % (len(bad), bad[0]["Source_1"]))

    # 2. THE PRIVACY INVARIANT. Not one staged description may carry private
    #    personal news. This is the invariant that must never be relaxed.
    priv = [r for r in rows if PRIVATE.search(r["Description"])]
    if priv:
        f.append("PRIVATE_PERSONAL_CONTENT_IN_OUTPUT: %d, e.g. %s"
                 % (len(priv), r"%s" % priv[0]["candidate_id"]))

    # 3. every candidate carries a source link
    nosrc = [r for r in rows if not r["Source_1"].startswith("http")]
    if nosrc:
        f.append("CANDIDATE_WITHOUT_SOURCE_LINK: %d" % len(nosrc))

    # 4. an intra-family row may never be countable
    leak = [r for r in rows if r["intra_family_reporting_change"] == "yes"
            and r["deal_status_std"] != "NOT_A_TRANSACTION"]
    if leak:
        f.append("INTRA_FAMILY_ROW_LEFT_COUNTABLE: %d" % len(leak))

    # 5. no value may be asserted without a basis quoting the source
    ghost = [r for r in rows if r["Announced_Value_USD"] and not r["value_basis"]]
    if ghost:
        f.append("VALUE_WITHOUT_BASIS: %d" % len(ghost))

    # 6. candidate ids unique
    dup = [k for k, v in Counter(r["candidate_id"] for r in rows).items() if v > 1]
    if dup:
        f.append("DUPLICATE_CANDIDATE_ID: %d, e.g. %s" % (len(dup), dup[0]))

    # 7. no host may have supplied three identical bodies AND produced rows
    byhost = defaultdict(Counter)
    for d in docs:
        if d.get("md5") and d["http_status"] == 200:
            byhost[d["host"]][d["md5"]] += 1
    poisoned = {h for h, c in byhost.items() if c and max(c.values()) >= 3}
    mined = {h for h, c in byhost.items()
             for d in docs if d["host"] == h and d.get("candidates")}
    both = sorted(poisoned & mined)
    if both:
        # only a failure if a document AFTER the third repeat was mined
        realbad = [d for d in docs if d["host"] in poisoned and d.get("candidates")
                   and "IDENTICAL_BODY_REPEAT" not in (d.get("note") or "")
                   and byhost[d["host"]][d["md5"]] >= 3]
        if realbad:
            f.append("MINED_A_REPEATED_BODY: %d docs, e.g. %s"
                     % (len(realbad), realbad[0]["url"]))
    return f


def selftest():
    base = dict.fromkeys(FIELDS, "")
    base.update(candidate_id="NLDEAL-1", cedar_uid="CE-OK",
                Source_1="https://example.org/news/1",
                Description="The Nation acquired a majority interest in Example LLC.",
                intra_family_reporting_change="no", deal_status_std="Closed")
    t = []
    r = dict(base, Source_1="https://www.sudrum.com/x")
    t.append(("restrictive", any("RESTRICTIVE_SOURCE_PRESENT" in x for x in verify([r], []))))
    r = dict(base, Description="Elder John Doe passed away Tuesday; he acquired "
                               "a majority interest in the family ranch.")
    t.append(("privacy", any("PRIVATE_PERSONAL_CONTENT" in x for x in verify([r], []))))
    r = dict(base, Source_1="")
    t.append(("nosource", any("CANDIDATE_WITHOUT_SOURCE_LINK" in x for x in verify([r], []))))
    r = dict(base, intra_family_reporting_change="yes", deal_status_std="Closed")
    t.append(("intrafamily", any("INTRA_FAMILY_ROW_LEFT_COUNTABLE" in x for x in verify([r], []))))
    r = dict(base, Announced_Value_USD="1000000", value_basis="")
    t.append(("valuebasis", any("VALUE_WITHOUT_BASIS" in x for x in verify([r], []))))
    t.append(("dupid", any("DUPLICATE_CANDIDATE_ID" in x
                           for x in verify([dict(base), dict(base)], []))))
    docs = [{"url": "https://h.org/%d" % i, "host": "h.org", "md5": "same",
             "http_status": 200, "candidates": 2, "note": ""} for i in range(3)]
    t.append(("repeatbody", any("MINED_A_REPEATED_BODY" in x
                                for x in verify([dict(base)], docs))))

    # POSITIVE CONTROL. A screen that rejects everything passes every negative
    # invariant above and finds nothing, which is the failure mode this project
    # calls a false absence. Prove the miner still fires on real deal language,
    # and prove the private-life screen suppresses the same sentence when it is
    # surrounded by community news.
    tgt = {"cedar_uid": "CE-T", "tribe_id": "T", "publisher": "Test Nation",
           "entity_class": "Federally recognized tribe", "state": "OK",
           "publication": "Test News", "channel_url": "https://t.org/news",
           "url": "https://t.org/news/1"}
    good = ("The Nation announced this week that its economic development arm "
            "has acquired a majority interest in Example Solutions LLC for "
            "$4.2 million, a transaction the council approved on March 4, 2025. "
            "The company will continue to operate from Tulsa.")
    rows, _dp = mine(good, tgt, {}, "md5")
    t.append(("miner_fires", len(rows) == 1 and rows[0]["Announced_Value_USD"] == "4200000"
              and rows[0]["deal_status_std"] == "Closed"))
    bad = ("Funeral services will be held Saturday. He is survived by four "
           "children. In earlier years he acquired a majority interest in the "
           "family store, which the family still runs.")
    rows2, dp2 = mine(bad, tgt, {}, "md5")
    t.append(("privacy_screen", rows2 == [] and dp2 == 1))
    fam = {"test nation": "root corp", "example solutions llc": "root corp"}
    rows3, _ = mine(good, tgt, fam, "md5")
    t.append(("intra_family_screen",
              len(rows3) == 1 and rows3[0]["deal_status_std"] == "NOT_A_TRANSACTION"))
    for name, fired in t:
        print("  selftest %-12s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(x for _n, x in t) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv and selftest():
            return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        st = summarize()
        print("verify OK - %d documents, %d candidates, 7 invariants held"
              % (st["documents_fetched"], st["candidates"]))
        return 0
    if "--repair-ids" in argv:
        return repair_ids()
    if "--refresh-values" in argv:
        return refresh_values()
    lim = None
    if "--limit" in argv:
        lim = int(argv[argv.index("--limit") + 1])
    return run(lim)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
