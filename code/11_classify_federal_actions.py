#!/usr/bin/env python3
"""
Cedar Press - Dataset 9, step 11: classify harvested Federal Register documents
into action types.

Input   data/clean/federal_actions_raw.csv   (from 10_pull_federal_register.py)
Output  data/clean/federal_actions.csv
        logs/11_classify_federal_actions_2026-08-05.log

Classification discipline
-------------------------
action_type is assigned ONLY from explicit text present in the document's own
title, abstract, or FR type field. Every classified row carries:

    action_type_signal        the exact substring that fired the rule
    action_type_rule          the named rule that fired
    action_type_source_field  title | abstract | type

so any label can be checked against the source text without re-reading the API.
Nothing is inferred from agency, docket pattern, date, or resemblance to a
neighbouring document. Anything that does not match an explicit signal is
'other'. 'other' is the honest answer, not a failure state - a document titled
'Notice of Meeting' genuinely does not say what kind of action it is.

Rules are ordered most-specific-first and the first match wins, because real FR
titles stack concepts: 'Land Acquisitions; Proclaiming Certain Lands as
Reservation' is a proclamation, not a generic trust acquisition, and 'Indian
Gaming; Approval of Tribal-State Compact' is a compact action, not a gaming
land decision.

Entity linking is deliberately NOT attempted. tribe_or_native_entity is written
empty for every row: resolving tribe names to the spine requires the spine's
alias history and the reconcile-queue rulings, and string-matching tribe names
out of notice titles is exactly the 'Cherokee Inc.' trap AGENTS.md forbids.
"""

import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
IN_CSV = CEDAR / "data" / "clean" / "federal_actions_raw.csv"
OUT_CSV = CEDAR / "data" / "clean" / "federal_actions.csv"
LOG_PATH = CEDAR / "logs" / "11_classify_federal_actions_2026-08-05.log"
TODAY = date.today().isoformat()

csv.field_size_limit(10_000_000)

# ------------------------------------------------------------------ rules ---
# (bucket, rule_name, regex). Order matters: first match wins.

RULES = [
    # --- the annual recognized-entities list and its corrections ------------
    ("recognition_list_update", "indian_entities_recognized",
     r"indian entities recognized"),
    ("recognition_list_update", "eligible_to_receive_services_list",
     r"entities recognized (?:by and )?(?:and )?eligible to receive services"),
    ("recognition_list_update", "list_of_federally_recognized",
     r"list of federally recognized (?:indian )?tribes?"),
    ("recognition_list_update", "federally_recognized_tribe_list_act",
     r"federally recognized indian tribe list act"),

    # --- Part 83 acknowledgment proceedings ---------------------------------
    ("federal_acknowledgment", "federal_acknowledgment_phrase",
     r"federal acknowledg\w*"),
    ("federal_acknowledgment", "petition_for_acknowledgment",
     r"petition\w*\s+for\s+(?:federal\s+)?acknowledg\w*"),
    ("federal_acknowledgment", "acknowledgment_as_indian_tribe",
     r"acknowledg\w*[^.]{0,80}\bas an? (?:indian )?tribe\b"),
    ("federal_acknowledgment", "finding_or_determination_on_acknowledgment",
     r"(?:proposed finding|final determination|reconsidered final "
     r"determination)[^.]{0,80}acknowledg\w*"),
    ("federal_acknowledgment", "acknowledgment_of_named_tribe",
     r"acknowledg\w*\s+of\s+(?:the\s+)?[^.]{0,60}\b(?:tribe|band|nation|"
     r"community|pueblo|rancheria)\b"),

    # --- reservation proclamations (25 U.S.C. 467 / sec. 7 IRA) -------------
    ("reservation_proclamation", "reservation_proclamation_phrase",
     r"reservation proclamation"),
    ("reservation_proclamation", "proclaiming_lands_as_reservation",
     r"proclaim\w*[^.]{0,100}\breservation\b"),
    ("reservation_proclamation", "proclamation_of_reservation",
     r"proclamation[^.]{0,80}\breservation\b"),
    ("reservation_proclamation", "lands_as_reservation",
     r"\blands?\b[^.]{0,60}\bas (?:an? |the )?(?:initial |part of the )?"
     r"reservation\b"),

    # --- ANCSA conveyances / selections (kept separate from lower-48 trust) --
    ("ancsa_conveyance", "ancsa_acronym",
     r"\bANCSA\b"),
    ("ancsa_conveyance", "alaska_native_claims_settlement_act",
     r"alaska native claims settlement act"),
    ("ancsa_conveyance", "alaska_native_claims_selection",
     r"alaska native claims? selection"),
    ("ancsa_conveyance", "alaska_conveyance",
     r"(?:interim )?conveyance[^.]{0,80}alaska native|"
     r"alaska native[^.]{0,80}(?:interim )?conveyance"),

    # --- tribal-state compacts (IGRA class III) -----------------------------
    ("tribal_state_compact", "tribal_state_compact_phrase",
     r"tribal[- ]state[^.]{0,60}compact"),
    ("tribal_state_compact", "class_iii_compact",
     r"class iii[^.]{0,60}compact"),
    ("tribal_state_compact", "gaming_compact",
     r"gaming compact"),
    ("tribal_state_compact", "compact_between_state_and_tribe",
     r"compact between[^.]{0,80}\b(?:state|tribe|nation|band)\b"),

    # --- gaming land / Indian lands determinations --------------------------
    ("gaming_land_decision", "two_part_determination",
     r"two[- ]part determination"),
    ("gaming_land_decision", "indian_lands_determination",
     r"indian lands (?:determination|opinion|eligibility)"),
    ("gaming_land_decision", "gaming_eligibility_of_land",
     r"gaming[^.]{0,80}\b(?:eligib\w+|land acquisition|acquisition of land)\b|"
     r"\b(?:eligib\w+|land acquisition|acquisition of land)\b[^.]{0,80}gaming"),
    ("gaming_land_decision", "gaming_facility_nepa",
     r"(?:environmental impact statement|environmental assessment|"
     r"record of decision|finding of no significant impact)[^.]{0,100}"
     r"\b(?:casino|gaming)\b|"
     r"\b(?:casino|gaming)\b[^.]{0,100}(?:environmental impact statement|"
     r"environmental assessment|record of decision)"),

    # --- fee-to-trust / land into trust (non-gaming, lower 48) --------------
    ("land_into_trust", "fee_to_trust",
     r"fee[- ]to[- ]trust"),
    ("land_into_trust", "land_into_trust_phrase",
     r"land[s]?\s+into\s+trust"),
    ("land_into_trust", "land_acquisition_heading",
     r"land acquisitions?\b"),
    ("land_into_trust", "trust_acquisition",
     r"trust acquisition"),
    ("land_into_trust", "acquire_in_trust",
     r"acquir\w*[^.]{0,80}\bin trust\b|"
     r"\bin trust\b[^.]{0,60}\bfor the (?:benefit of the )?[^.]{0,60}"
     r"\b(?:tribe|band|nation|community|pueblo|rancheria)\b"),

    # --- liquor ordinances (25 U.S.C. 1161) ---------------------------------
    ("liquor_ordinance", "liquor_ordinance_phrase",
     r"liquor[^.]{0,40}\b(?:ordinance|code|act|law|regulation|statute)\b|"
     r"\b(?:ordinance|code)\b[^.]{0,40}liquor"),
    ("liquor_ordinance", "alcoholic_beverage_ordinance",
     r"alcohol(?:ic)?[^.]{0,40}\b(?:ordinance|code)\b"),

    # --- irrigation project rates -------------------------------------------
    ("irrigation_rates", "irrigation_rate_adjustment",
     r"irrigation[^.]{0,80}\b(?:rate|assessment|charge|fee|operation and "
     r"maintenance)\w*\b|"
     r"\brate\w*\b[^.]{0,80}irrigation"),

    # --- funding notices -----------------------------------------------------
    ("grant_solicitation", "notice_of_funding_opportunity",
     r"notice of funding (?:opportunity|availability)|funding opportunity "
     r"announcement|\bNOFO\b|\bNOFA\b"),
    ("grant_solicitation", "solicitation_of_applications",
     r"solicitation of (?:applications|proposals|grant)|"
     r"request for (?:applications|proposals)|"
     r"applications? (?:are )?(?:now )?(?:being )?(?:solicited|accepted|"
     r"invited)"),
    ("grant_solicitation", "availability_of_funds",
     r"availability of (?:grant )?funds|announcement of (?:grant|funding)"),

    # --- consultation (tribal context required) ------------------------------
    ("consultation", "tribal_consultation_phrase",
     r"tribal consultation|consultation with (?:indian |federally recognized )"
     r"?tribe|government[- ]to[- ]government consultation|"
     r"consultation[^.]{0,60}\b(?:indian tribes?|tribal nations?|"
     r"alaska native)\b|"
     r"\b(?:indian tribes?|tribal|alaska native)\b[^.]{0,60}consultation"),
]

RULES = [(b, n, re.compile(p, re.IGNORECASE)) for b, n, p in RULES]

# Buckets that may only be assigned from the TITLE.
#
# 'consultation' is the case that forces this rule. Agencies routinely recite
# in an abstract that tribal consultation was conducted before issuing a rule -
# that sentence is evidence consultation happened somewhere, not evidence that
# THIS document is a consultation notice. Observed on real 2024 rows: 'Tribal
# General Welfare Benefits' (a Rule) and an Alaska subsistence rule were both
# pulled into 'consultation' by such a recital. A document is a consultation
# action when its title says so.
TITLE_ONLY_BUCKETS = {"consultation"}

# The FR 'type' field is itself an explicit signal for rulemaking stage.
RULEMAKING_TYPES = {"Rule", "Proposed Rule"}

BUCKETS = [
    "reservation_proclamation", "land_into_trust", "ancsa_conveyance",
    "gaming_land_decision", "tribal_state_compact", "liquor_ordinance",
    "federal_acknowledgment", "recognition_list_update", "consultation",
    "rulemaking", "irrigation_rates", "grant_solicitation", "other",
]


def classify(title, abstract, doc_type):
    """Return (bucket, rule_name, matched_text, source_field)."""
    for field_name, text in (("title", title), ("abstract", abstract)):
        if not text:
            continue
        for bucket, rule_name, pat in RULES:
            if field_name != "title" and bucket in TITLE_ONLY_BUCKETS:
                continue
            m = pat.search(text)
            if m:
                return bucket, rule_name, m.group(0)[:160], field_name
    if (doc_type or "").strip() in RULEMAKING_TYPES:
        return "rulemaking", "fr_document_type", doc_type.strip(), "type"
    return "other", "", "", ""


def main():
    if not IN_CSV.exists():
        raise SystemExit(f"missing input: {IN_CSV} (run 10_ first)")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(LOG_PATH, "w", encoding="utf-8")

    def log(msg=""):
        print(msg, flush=True)
        log_fh.write(msg + "\n")

    by_type, by_rule, by_net = Counter(), Counter(), Counter()
    by_hit = Counter()
    by_doctype_year = {}
    by_type_year, samples = {}, {}
    n_rows = 0

    class _Y(dict):
        def __missing__(self, k):
            self[k] = Counter()
            return self[k]

    by_doctype_year = _Y()

    # Streamed: the raw file runs to six figures of rows, so it is never held
    # in memory. Only counters and five sample rows per bucket are retained.
    with open(IN_CSV, encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        in_fields = reader.fieldnames or []
        out_fields = (in_fields
                      + ["action_type", "action_type_rule", "action_type_signal",
                         "action_type_source_field", "tribe_or_native_entity",
                         "classified_date"])
        with open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields)
            w.writeheader()
            for r in reader:
                bucket, rule_name, signal, field_name = classify(
                    r.get("title", ""), r.get("abstract", ""), r.get("type", ""))
                r["action_type"] = bucket
                r["action_type_rule"] = rule_name
                r["action_type_signal"] = signal
                r["action_type_source_field"] = field_name
                r["tribe_or_native_entity"] = ""   # spine job, left empty
                r["classified_date"] = TODAY
                w.writerow(r)

                n_rows += 1
                by_type[bucket] += 1
                if rule_name:
                    by_rule[(bucket, rule_name)] += 1
                by_net[(bucket, r.get("net_caught", ""))] += 1
                by_hit[(bucket, r.get("title_abstract_term_hit", ""))] += 1
                by_doctype_year[(r.get("publication_date") or "")[:4]][
                    r.get("type") or "(blank)"] += 1
                year = (r.get("publication_date") or "")[:4]
                by_type_year.setdefault(bucket, Counter())[year] += 1
                s = samples.setdefault(bucket, [])
                if len(s) < 5:
                    s.append((r.get("publication_date", ""), r.get("title", ""),
                              signal, rule_name, field_name))

    log("Cedar Press Dataset 9 - classification")
    log(f"input  {IN_CSV}")
    log(f"output {OUT_CSV}")
    log(f"rows   {n_rows:,}")
    log("")
    log("action_type counts:")
    for b in BUCKETS:
        log(f"  {by_type.get(b, 0):>8,}  {b}")
    log("")
    log("rule firings (which explicit signal did the work):")
    for (b, n), v in by_rule.most_common():
        log(f"  {v:>8,}  {b} :: {n}")
    log("")
    log("classified (non-other) share: "
        f"{1 - by_type['other'] / max(n_rows, 1):.1%}")
    log("")
    log("action_type x net_caught:")
    for b in BUCKETS:
        parts = [f"{net}={by_net[(b, net)]:,}"
                 for net in ("agency", "keyword", "both")
                 if by_net[(b, net)]]
        log(f"  {b:<26} {'  '.join(parts)}")
    log("")
    log("action_type x title_abstract_term_hit")
    log("  (hit = a harvest term actually appears in this document's own title")
    log("   or abstract; no = the document matched on full text only, i.e. it")
    log("   mentions the term somewhere in the body. This is the relevance")
    log("   dimension - action_type says what kind of action, this says whether")
    log("   the document is about Indian Country on its face.)")
    for b in BUCKETS:
        h, nh = by_hit[(b, "1")], by_hit[(b, "0")]
        tot = h + nh
        if tot:
            log(f"  {b:<26} hit={h:>7,}  full-text-only={nh:>7,}  "
                f"({h / tot:.0%} on-face)")
    log("")
    log("FR document type by publication year (metadata coverage check):")
    for y in sorted(by_doctype_year):
        c = by_doctype_year[y]
        log(f"  {y}  " + "  ".join(f"{k}={v:,}" for k, v in c.most_common()))
    log("")
    log("action_type by publication year:")
    years = sorted({y for c in by_type_year.values() for y in c})
    for b in BUCKETS:
        c = by_type_year.get(b, Counter())
        log(f"  [{b}] " + " ".join(f"{y}:{c[y]}" for y in years if c[y]))
    log("")
    log("sample titles per action_type (verification aid):")
    for b in BUCKETS:
        log(f"\n  [{b}]")
        if not samples.get(b):
            log("    (none)")
        for pub, title, signal, rule_name, field_name in samples.get(b, []):
            log(f"    {pub}  {title[:110]}")
            if rule_name:
                log(f"        signal: {signal[:90]!r} "
                    f"({rule_name}, {field_name})")
    log("")
    log("tribe_or_native_entity left empty on every row by design "
        "(entity linking runs off the spine, not off notice titles).")
    log_fh.close()


if __name__ == "__main__":
    sys.exit(main())
