#!/usr/bin/env python3
"""
Cedar Press - 352: unlink the false entity links in `foia_request_index.csv`.
This is FA-02, at the shipping table.

THE DEFECT
----------
`docs/ANOMALY_REPORT.md` FA-02, **STILL DEFECTIVE**:

    data/clean/foia_request_index.csv   9,481 rows · 453 linked
      AKNF-GEORGT-00-CALSTA-ASVCPR   94 rows      <- Native Village of
                                                     Georgetown, ALASKA
      TRBF-ENTPRS-00                 17 rows

**92 of the 94 Georgetown rows matched inside a LIST OF EMAIL DOMAINS** a
requester asked the agency to search:

    ... 'wcl.american.edu' OR 'cpl.ucla.edu' OR 'ucla.edu' OR
        'georgetown.edu' OR 'law.georgetown.edu' OR 'stanford.edu' ...

The other two matched **"Georgetown Climate Center"**, a Washington DC policy
centre, in a list beside Earthjustice and the Sierra Club. None of the 94
names an Alaska Native village; not one row anywhere in the file contains
"Native Village of Georgetown".

`TRBF-ENTPRS-00`'s canonical name in the spine is literally **"Enterprise"**
(Enterprise Rancheria), so the token catches any organisation with the common
English noun in its name. What it actually caught: `Solutions for Enterprise-
Wide Procurement (SEWP) V` (three separate requests), `D--JTM ENTERPRISE ZOOM
LICENSES`, the **American Enterprise Institute**, the **Competitive Enterprise
Institute**, `Enterprise Security and Assessment Support Services`, an
`Enterprise Data Inventory`, `Bing Chat Enterprise`, `Enterprise Human
Resources Integration (EHRI)`, the `Superfund Enterprise Management System`,
a contractor called `Elite Enterprise`, the phrase "Criminal Enterprise", and
an obituary on `examiner-enterprise`.

WHY DEMOTION WAS NOT ENOUGH
---------------------------
A prior pass wrote, on every one of these rows:

    DISPUTED_FREE_TEXT_SINGLE_TOKEN: ... Link retained, demoted, staged for a
    ruling.

That was the right caution at the time and it is the wrong END STATE. The rows
sit at `tribe_entity_link_tier = B` in a column called `tribe_entity_id`, and
any consumer reading that column - a concentration count, an entity profile, a
"which tribes appear most in FOIA logs" chart - reads a link, not a caveat.
**A demoted wrong link is still a wrong link in a shipping column.** The
ruling is made here.

WHAT IS PRESERVED, DELIBERATELY
-------------------------------
`tribe_mentioned` and `tribe_match_phrase` - the token-match provenance - are
UNTOUCHED, and the withdrawn id is kept in a new `tribe_entity_id_withdrawn`
column. The correction has to be VISIBLE and reversible, not erased: the next
reader must be able to see that `georgetown` fired, what it fired on, and who
refused it. The prior DISPUTED audit text is carried forward verbatim inside
the new audit string - this project does not delete reasoning, it supersedes it.

WHY BLANK AND NOT TIER X
------------------------
`169_build_identifier_graph.py` treats X as a statement about the IDENTIFIER.
`TRBF-ENTPRS-00` is a perfectly sound identifier for Enterprise Rancheria and
blacklisting it would suppress the two rows in this same file that genuinely
are that tribe, plus every correct attribution elsewhere. The identifier is
sound; 109 specific LINKS are not. Unlink the links.

THE TWO ENTERPRISE ROWS THAT ARE KEPT, AND WHY
----------------------------------------------
  DOI-2025-001151  "...trust application by the Enterprise Rancheria of Maidu
                   Indians of California" - the full tribal name is present.
                   CONFIRMED, and the audit now says so.
  DOI-2025-001646  an AS-IA request for "Secretarial Decision Letters,
                   regarding a land-to-trust application by the Enterprise" -
                   the parsed description TRUNCATES mid-name. It is not
                   demonstrably wrong, and an unlink needs evidence just as
                   much as a link does. Kept at tier B, with the truncation
                   named in the audit so nobody re-litigates it from scratch.

Reads/Writes  data/clean/foia_request_index.csv               (in place)
Writes        review/foia_entity_links_withdrawn_2026-08-26.csv
              data/clean/cedar_correction_register.csv        (append)

REBUILD THAT WOULD UNDO THIS
----------------------------
`code/136_build_congressional_correspondence_and_foia_index.py` rebuilds this
file from the parsed FOIA logs; `code/168_link_adjudication_hubs.py` is an
in-place linker on it (50 rows carry `entity_link_built_by_script =
code/168_link_adjudication_hubs.py`). Standing rule: THE ENRICHER RUNS LAST.
After any 136 rebuild, run 168, then 352.
"""

import csv
import importlib.util
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = "352_unlink_false_foia_entity_links.py"

SRC = CLEAN / "foia_request_index.csv"
OUT_REVIEW = REVIEW / f"foia_entity_links_withdrawn_{TODAY}.csv"

NEW_COLS = ["tribe_entity_id_withdrawn", "tribe_entity_link_withdrawn",
            "tribe_entity_link_withdrawn_reason",
            "tribe_entity_link_withdrawn_evidence_verbatim",
            "tribe_entity_link_withdrawn_by_script",
            "tribe_entity_link_withdrawn_date"]

TEXT_COLS = ["request_description", "requester_organization",
             "organization_mentioned", "official_mentioned", "requester",
             "issue_terms_matched"]

GEORGT = "AKNF-GEORGT-00-CALSTA-ASVCPR"
ENTPRS = "TRBF-ENTPRS-00"

EDU_DOMAIN = re.compile(r"georgetown\.edu", re.I)
CLIMATE = re.compile(r"georgetown\s+climate", re.I)
RANCHERIA = re.compile(r"enterprise\s+rancheria", re.I)
TRUST_CONTEXT = re.compile(
    r"land[\s-]*(?:in)?to[\s-]*trust|trust acquisition|secretarial decision",
    re.I)


def blob(r):
    return " | ".join((r.get(c) or "") for c in TEXT_COLS)


def window(text, pat, pad=90):
    m = pat.search(text)
    if not m:
        return ""
    return re.sub(r"\s+", " ",
                  text[max(0, m.start() - pad): m.end() + pad]).strip()


def classify(r):
    """-> (action, reason, evidence_verbatim)

    action is UNLINK, CONFIRM (the link is right and the audit should say so)
    or RETAIN (not demonstrably wrong; stays disputed, with the doubt named).
    """
    eid = (r.get("tribe_entity_id") or "").strip()
    b = blob(r)
    if eid == GEORGT:
        if EDU_DOMAIN.search(b):
            return ("UNLINK",
                    "The phrase 'georgetown' was matched inside a list of "
                    "EMAIL DOMAINS the requester asked the agency to search "
                    "('georgetown.edu', 'law.georgetown.edu'), alongside "
                    "ucla.edu and stanford.edu. An internet domain in a search "
                    "instruction is not a party to the request, and it is not "
                    "the Native Village of Georgetown, Alaska.",
                    window(b, EDU_DOMAIN))
        if CLIMATE.search(b):
            return ("UNLINK",
                    "The phrase 'georgetown' was matched on GEORGETOWN CLIMATE "
                    "CENTER, a Washington DC policy centre, listed beside "
                    "Earthjustice, the Sierra Club and the Center for American "
                    "Progress. Not the Native Village of Georgetown, Alaska.",
                    window(b, CLIMATE))
        return ("UNLINK",
                "The phrase 'georgetown' was matched in free-text prose with "
                "no Alaska Native village anywhere in the request. No row in "
                "this file contains 'Native Village of Georgetown'.",
                window(b, re.compile("georgetown", re.I)))

    if eid == ENTPRS:
        if RANCHERIA.search(b):
            return ("CONFIRM",
                    "The full tribal name 'Enterprise Rancheria' is present in "
                    "the request text. The link is correct.",
                    window(b, RANCHERIA))
        if TRUST_CONTEXT.search(b) and (r.get("agency_code") or "") == "BIA":
            return ("RETAIN",
                    "An AS-IA/BIA land-to-trust decision-letter request whose "
                    "PARSED DESCRIPTION TRUNCATES immediately after '...by the "
                    "Enterprise'. Not demonstrably wrong, so it is not "
                    "unlinked - an unlink needs evidence exactly as much as a "
                    "link does. Stays tier B, disputed, with the truncation "
                    "named so it is not re-litigated from scratch.",
                    window(b, TRUST_CONTEXT))
        return ("UNLINK",
                "TRBF-ENTPRS-00's canonical name is the common English noun "
                "'Enterprise', so the token matches any organisation carrying "
                "the word. The subject here is not a tribe - see the verbatim "
                "evidence on this row.",
                window(b, re.compile("enterprise", re.I)))
    return ("", "", "")


def load_register():
    spec = importlib.util.spec_from_file_location(
        "reg354", CODE / "354_correction_register.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def declare(withdrawn):
    """One register row per (entity_id, FOIA REQUEST).

    The subject key here is the REQUEST, never `tribe_match_phrase`. The
    phrase for `TRBF-ENTPRS-00` is the bare word 'Enterprise', and two rows
    carrying that same phrase are CORRECT - a pair-level invariant on the
    phrase cannot express a row-level ruling, and it also flags 306
    `prime_contracts` rows whose recipient name merely contains the English
    word. `354_correction_register.py` records why at length.
    """
    reg = load_register()
    # One FOIA request can occupy more than one parsed row (DOI-2026-000750
    # does), so the SUBJECT is aggregated before it is declared - otherwise
    # `rows_affected` would say 1 about 2 rows and the second declaration
    # would collapse into the first on its content-addressed id.
    agg = {}
    for d in withdrawn:
        k = (d["withdrawn_entity_id"], d["foia_request_id"])
        a = agg.setdefault(k, {"n": 0, "reason": d["reason"]})
        a["n"] += 1
    decl = []
    for (eid, rid), a in sorted(agg.items()):
        decl.append({
            "finding_id": "FA-02",
            "entity_id": eid,
            "withdrawn_key": rid,
            "table": SRC.name,
            "column_unlinked": "tribe_entity_id",
            "rows_affected": a["n"],
            "rows_removed": 0,
            "action": "UNLINK",
            "repointed_to": "",
            "provenance_preserved":
                "tribe_mentioned; tribe_match_phrase; "
                "tribe_entity_id_withdrawn; tribe_entity_link_audit",
            "reason": a["reason"],
        })
    return reg.record(decl, SCRIPT)


def declare_from_markers(rows):
    withdrawn = [{
        "foia_request_id": r.get("foia_request_id", ""),
        "withdrawn_entity_id": (r.get("tribe_entity_id_withdrawn") or "").strip(),
        "reason": r.get("tribe_entity_link_withdrawn_reason", ""),
    } for r in rows
        if (r.get("tribe_entity_link_withdrawn") or "") == "1"
        and (r.get("tribe_entity_link_withdrawn_by_script") or "") == SCRIPT]
    n = declare(withdrawn)
    print(f"  {len(withdrawn)} declaration(s) re-asserted, {n} newly written.")
    return 0


def main():
    print("=== Cedar Press 352: unlink false FOIA entity links ===\n")

    before_mtime = SRC.stat().st_mtime
    rows = read_csv(SRC)
    fields = list(rows[0].keys())
    print(f"  {SRC.name}: {len(rows):,} rows, {len(fields)} columns")
    linked_before = sum(1 for r in rows if (r.get("tribe_entity_id") or "").strip())
    print(f"  entity-linked before: {linked_before}")

    for c in NEW_COLS:
        if c not in fields:
            fields.append(c)

    actions = Counter()
    withdrawn = []
    for r in rows:
        for c in NEW_COLS:
            r[c] = r.get(c) or ""
        eid = (r.get("tribe_entity_id") or "").strip()
        if eid not in (GEORGT, ENTPRS):
            continue
        action, reason, ev = classify(r)
        actions[(eid, action)] += 1
        prior = (r.get("tribe_entity_link_audit") or "").strip()
        if action == "UNLINK":
            r["tribe_entity_id_withdrawn"] = eid
            r["tribe_entity_link_withdrawn"] = "1"
            r["tribe_entity_link_withdrawn_reason"] = reason
            r["tribe_entity_link_withdrawn_evidence_verbatim"] = ev
            r["tribe_entity_link_withdrawn_by_script"] = SCRIPT
            r["tribe_entity_link_withdrawn_date"] = TODAY
            r["tribe_entity_id"] = ""
            r["tribe_entity_link_tier"] = ""      # UNLINKED. Never X - see docstring.
            r["tribe_entity_link_audit"] = (
                f"UNLINKED_FALSE_MATCH ({TODAY}, {SCRIPT}): {reason} "
                f"EVIDENCE: \"{ev}\" "
                f"PROVENANCE KEPT: tribe_mentioned, tribe_match_phrase, "
                f"tribe_entity_id_withdrawn. PRIOR AUDIT: {prior}")
            withdrawn.append({
                "foia_request_id": r.get("foia_request_id", ""),
                "agency_code": r.get("agency_code", ""),
                "withdrawn_entity_id": eid,
                "tribe_mentioned": r.get("tribe_mentioned", ""),
                "tribe_match_phrase": r.get("tribe_match_phrase", ""),
                "reason": reason, "evidence_verbatim": ev,
                "prior_audit": prior,
                "withdrawn_by_script": SCRIPT, "withdrawn_date": TODAY})
        elif action == "CONFIRM":
            r["tribe_entity_link_audit"] = (
                f"CONFIRMED ({TODAY}, {SCRIPT}): {reason} "
                f"EVIDENCE: \"{ev}\" PRIOR AUDIT: {prior}")
        elif action == "RETAIN":
            r["tribe_entity_link_audit"] = (
                f"DISPUTED_RETAINED ({TODAY}, {SCRIPT}): {reason} "
                f"EVIDENCE: \"{ev}\" PRIOR AUDIT: {prior}")

    print("\n  dispositions:")
    for (eid, a), n in sorted(actions.items()):
        print(f"    {eid:32s} {a:8s} {n:>4}")

    if not withdrawn:
        # ALREADY APPLIED. Re-assert the declaration from the file's own
        # markers - see the note in 350; a register that only the first run
        # can write is a register that cannot be rebuilt after it is lost.
        print("\n  no live false links; re-asserting the declaration from the "
              "withdrawal markers already in the file.")
        return declare_from_markers(rows)

    if SRC.stat().st_mtime != before_mtime:
        print(f"\n  !! {SRC.name} CHANGED UNDER US. Refusing to write.")
        return 2

    bak = SRC.with_name(SRC.name + f".bak_{TODAY}_pre_{SCRIPT}")
    if not bak.exists():
        bak.write_bytes(SRC.read_bytes())
        print(f"\n  backed up -> {bak.name}")

    part = SRC.with_suffix(SRC.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(part, SRC)
    print(f"  wrote {SRC.name}")

    REVIEW.mkdir(parents=True, exist_ok=True)
    with open(OUT_REVIEW, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(withdrawn[0].keys()))
        w.writeheader()
        for d in withdrawn:
            w.writerow(d)
    print(f"  wrote {OUT_REVIEW.relative_to(CEDAR)}")

    n = declare(withdrawn)
    print(f"  declared {n} correction(s) in the register")

    back = read_csv(SRC)
    still_g = sum(1 for r in back
                  if (r.get("tribe_entity_id") or "").strip() == GEORGT)
    still_e = sum(1 for r in back
                  if (r.get("tribe_entity_id") or "").strip() == ENTPRS)
    linked = sum(1 for r in back if (r.get("tribe_entity_id") or "").strip())
    top = Counter((r.get("tribe_entity_id") or "").strip()
                  for r in back if (r.get("tribe_entity_id") or "").strip())
    print(f"\n  RE-READ: {len(back):,} rows · entity-linked "
          f"{linked_before} -> {linked}")
    print(f"    {GEORGT}: 94 -> {still_g}  (must be 0)")
    print(f"    {ENTPRS}: 17 -> {still_e}  (the 2 evidenced rows)")
    print(f"    top linked entities now: "
          f"{', '.join(f'{k} x{v}' for k, v in top.most_common(6))}")
    return 0 if still_g == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
