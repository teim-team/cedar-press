#!/usr/bin/env python3
"""
Cedar Press - 65: Withdraw lobbying attributions barred by organisation type.

THE LIVE DEFECT
---------------
Dataset 4 attributes **324 filings and $28.71M of SALT RIVER PROJECT's lobbying
spend to the Salt River Pima-Maricopa Indian Community**, matched on the alias
`river salt`. SRP is an Arizona public power and irrigation district. Also
wrong: Coeur d'Alene MINES ($2.96M) and the CITY OF Santa Rosa ($2.31M).

That is the "never falsely attribute" rule being broken in a launch-tier
dataset, so this is a WITHDRAWAL, not a build.

WHY NOT JUST DEMOTE EVERY MEDIUM MATCH
--------------------------------------
Because the medium tier is a mixture, and most of it is right. Also matched at
medium confidence, and correctly: Santa Ynez Band of Chumash Indians ($5.75M),
Forest County Potawatomi Community ($4.61M), Ho-Chunk Nation Legislature
($3.51M), Cook Inlet Region Incorporated ($2.81M), White Mountain Apache Tribe
($2.35M). Blanket demotion would discard $60M+ of correct attribution to remove
$34M of wrong.

The distinguishing feature is not the confidence score and not word order
(`chunk ho` is Ho-Chunk and correct). It is the ORGANISATION TYPE declared in
the client's own name. A public power district, a mining company and a
municipality are legal forms that a federally recognised tribe, an ANC or an NHO
cannot be. That is a fact about the name, not a similarity judgement.

WHAT THIS DOES NOT TOUCH
------------------------
- Anything Elijah ruled by hand.
- Any high-confidence match.
- Any client whose name carries a type marker but IS the entity - e.g. an
  authority or a housing authority owned by a tribe. The bar list below is
  restricted to forms that are definitionally not a Native entity.

Reads  data/clean/native_entity_lobbying_disclosures.csv
Writes data/clean/native_entity_lobbying_disclosures.csv  (flagged in place)
       review/lobbying_withdrawn_by_org_type.csv
"""

import csv
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

SRC = CLEAN / "native_entity_lobbying_disclosures.csv"

# Legal forms a Native ENTITY cannot be. Each is a statement about what the
# organisation IS, not about how similar its name looks.
BARRED = [
    (re.compile(r"^\s*city of\b", re.I), "a municipality"),
    (re.compile(r"^\s*town of\b", re.I), "a municipality"),
    (re.compile(r"^\s*county of\b|\bcounty government\b", re.I), "a county"),
    (re.compile(r"^\s*state of\b", re.I), "a state government"),
    (re.compile(r"\bmines?\b|\bmining (co|corp|company)\b", re.I),
     "a mining company"),
    (re.compile(r"\b(power|irrigation|water|utility|electric)\s+district\b", re.I),
     "a special district"),
    (re.compile(r"\bsalt river project\b", re.I),
     "the Salt River Project, an Arizona public power and irrigation district - "
     "NOT the Salt River Pima-Maricopa Indian Community"),
    (re.compile(r"\buniversity\b|\bcollege of\b", re.I),
     "a university (tribal colleges are ruled separately, by name)"),
    (re.compile(r"\bcooperative\b|\bco-?op\b|\bemc\b", re.I),
     "a member cooperative"),
    (re.compile(r"\bschool district\b", re.I), "a school district"),
    (re.compile(r"\bchamber of commerce\b", re.I), "a chamber of commerce"),
]

# Names that LOOK barred but are genuinely Native, checked by hand. A guard
# without an exception list eventually eats something true.
EXEMPT = re.compile(
    r"salish kootenai college|haskell|dine college|ilisagvik|"
    r"college of the menominee|sinte gleska|oglala lakota college|"
    r"tribal college|navajo technical", re.I)


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 65: organisation-type guard on lobbying ===\n")
    rows = read_csv(SRC)
    print(f"filings: {len(rows):,}")
    shutil.copy2(SRC, SRC.with_suffix(f".csv.bak_{TODAY}_pre65"))

    fields = list(rows[0].keys())
    for c in ("org_type_barred", "org_type_reason"):
        if c not in fields:
            fields.append(c)

    withdrawn, kept_exempt = [], Counter()
    per_client = defaultdict(lambda: [0, 0.0, "", ""])

    for r in rows:
        r.setdefault("org_type_barred", "")
        r.setdefault("org_type_reason", "")
        client = (r.get("client_name") or "").strip()
        if not client or not (r.get("canonical_name") or "").strip():
            continue
        if EXEMPT.search(client):
            kept_exempt[client] += 1
            continue
        for rx, why in BARRED:
            if rx.search(client):
                r["org_type_barred"] = "1"
                r["org_type_reason"] = why
                # Withdraw the attribution; keep the filing.
                r["canonical_name"] = ""
                r["entity_id"] = ""
                r["match_confidence"] = "withdrawn_org_type"
                k = per_client[client]
                k[0] += 1
                k[1] += float(r.get("spend_usd") or 0)
                k[2], k[3] = why, r.get("matched_alias", "")
                break

    for client, (n, usd, why, alias) in sorted(
            per_client.items(), key=lambda kv: -kv[1][1]):
        withdrawn.append({"client_name": client, "n_filings": n,
                          "spend_usd": round(usd, 2), "barred_because": why,
                          "matched_via_alias": alias, "withdrawn": TODAY})

    total = sum(w["spend_usd"] for w in withdrawn)
    print(f"\n  clients withdrawn : {len(withdrawn)}")
    print(f"  filings affected  : {sum(w['n_filings'] for w in withdrawn):,}")
    print(f"  spend withdrawn   : ${total/1e6:,.2f}M\n")
    for w in withdrawn[:10]:
        print(f"     ${w['spend_usd']/1e6:7.2f}M  {w['client_name'][:38]:38s} "
              f"{w['barred_because'][:40]}")
    if kept_exempt:
        print(f"\n  exempted (genuinely Native despite the marker): "
              f"{len(kept_exempt)}")

    with open(SRC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\n  rewrote {SRC.relative_to(CEDAR)}")

    if withdrawn:
        p = REVIEW / "lobbying_withdrawn_by_org_type.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(withdrawn[0].keys()))
            w.writeheader()
            w.writerows(withdrawn)
        print(f"  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
