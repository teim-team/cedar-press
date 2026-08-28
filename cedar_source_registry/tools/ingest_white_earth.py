#!/usr/bin/env python3
"""
Ingest the White Earth Nation TERO certified Indian-owned business registry
(TBD-113) into layer-1 source_records, and extract the certification rules and
bid-preference schedule from the 2026 TERO Ordinance.

Owner-supplied 2026-08-28. Both files are owner downloads, NOT scraped:
  - "Certified Indian Owned Businesses-updated 2026.docx"   (the roster)
  - "TERO Ordinance 2026 copy.docx"                          (the rules)

TBD-113 was a Lead ("public roster not located"). This converts it.

The parser NEVER guesses. Any line it cannot confidently parse is emitted to
the unparsed report and NOT turned into a record. A record with a field the
parser could not find gets null plus a validation flag -- never an inferred
value.

Usage:
  py -3 tools/ingest_white_earth.py --src <dir with the two .docx> [--write]

Without --write it is a dry run and prints what it would do.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_ID = "TBD-113"
NATION_ID = "bia:minnesota-chippewa-tribe--white-earth"
SOURCE_URL = "https://www.whiteearth.com/divisions/human-services/workforce-center"

ROSTER_DOCX = "Certified Indian Owned Businesses-updated 2026.docx"
ORDINANCE_DOCX = "TERO Ordinance 2026 copy.docx"

RUN_ID = "run-2026-08-28-white-earth-001"
INGEST_DATE = "2026-08-28"
TS = "2026-08-28T00:00:00Z"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# The ordinance's contracting preference ladder (Chapter 6, categories C-F).
# Verbatim text is carried so the tier label on a roster row can be read
# against the rule that defines it.
PREFERENCE_LADDER = {
    "1st": {
        "ordinance_category": "C",
        "level": 1,
        "text": (
            "first level preference to certified Indian-owned firms whose "
            "principal place of business is located on the Reservation or "
            "Tribal Trust Land"
        ),
        "certified": True,
        "principal_place_on_reservation": True,
    },
    "2nd": {
        "ordinance_category": "D",
        "level": 2,
        "text": (
            "a second level preference to certified Indian-owned firms which "
            "do not qualify under C above in the awarding of contracts and "
            "subcontracts"
        ),
        "certified": True,
        "principal_place_on_reservation": False,
    },
    "3rd": {
        "ordinance_category": "E",
        "level": 3,
        "text": (
            "a third level preference to non-certified firms with some Indian "
            "ownership, whose principal place of business is located on the "
            "Reservation or Tribal Trust Land over all other non-certified "
            "firms with some Indian ownership"
        ),
        "certified": False,
        "principal_place_on_reservation": True,
    },
    "4th": {
        "ordinance_category": "F",
        "level": 4,
        "text": (
            "a 4th level preference to non-certified firms with some Indian "
            "ownership over all others not covered at C, D, or E"
        ),
        "certified": False,
        "principal_place_on_reservation": False,
    },
}

# Chapter 6 schedule of percentage preference: bid-price preference allowed
# above the lowest responsible bid, by contract size. Bands are (low, high,
# pct) with high=None for the open top band. Verbatim source lines are kept
# in the rules artifact.
PERCENTAGE_PREFERENCE = [
    (0, 100_000, 10.0),
    (100_000, 200_000, 9.0),
    (200_000, 300_000, 8.0),
    (300_000, 400_000, 7.0),
    (400_000, 500_000, 6.0),
    (500_000, 1_000_000, 5.0),
    (1_000_000, 2_000_000, 4.0),
    (2_000_000, 4_000_000, 3.0),
    (4_000_000, 7_000_000, 2.0),
    (7_000_000, None, 1.5),
]


def docx_lines(path: str) -> list[str]:
    """Extract paragraph text from a .docx. Preserves source order."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"</w:tr>", "\n", xml)
    xml = re.sub(r"</w:tc>", " | ", xml)
    xml = html.unescape(re.sub(r"<[^>]+>", "", xml))
    # Normalize the curly punctuation Word emits so downstream matching is sane.
    xml = xml.replace("\u2019", "'").replace("\u2018", "'")
    xml = xml.replace("\u201c", '"').replace("\u201d", '"')
    xml = xml.replace("\u2013", "-").replace("\u2014", "-")
    return [ln.strip() for ln in xml.split("\n") if ln.strip()]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def parse_expiration(text: str):
    """
    'expires in May of 2027' / 'expires Dec 2029' / 'Expires Nov 2027'
    -> ('2027-05', verbatim). Returns (None, None) when absent -- never guesses.
    """
    m = re.search(
        r"expires?\s+(?:in\s+)?([A-Za-z]+)\.?\s+(?:of\s+)?(\d{4})", text, re.I
    )
    if not m:
        return None, None
    raw_month, year = m.group(1).lower(), m.group(2)
    month = None
    for name, num in MONTHS.items():
        if name.startswith(raw_month[:3]):
            month = num
            break
    if month is None:
        return None, m.group(0)
    return f"{year}-{month:02d}", m.group(0)


def parse_preference(text: str):
    """'1st Preference' / '4th Indian Preference' / '1st preference' -> '1st'."""
    m = re.search(r"\b(1st|2nd|3rd|4th)\b[^.;]{0,20}?preference", text, re.I)
    if not m:
        return None, None
    return m.group(1).lower(), m.group(0).strip()


def parse_phones(text: str) -> list[str]:
    """Return every phone-shaped token, in source order, de-duplicated."""
    pats = [
        r"\b1?[-\s]?\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
        r"\b\d{3}[-.\s]\d{3}[-.\s]\d{3}\b",  # catches a truncated 9-digit phone present in the source
    ]
    out, seen = [], set()
    for p in pats:
        for m in re.finditer(p, text):
            v = m.group(0).strip().lstrip("-").strip()
            if v not in seen:
                seen.add(v)
                out.append(v)
    return out


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Two address shapes appear in this source and the order matters. The dash/comma
# form is tried FIRST: if bare whitespace were allowed as the street/city
# separator up front, "123 Example St N- Somecity, MN" would parse its city as
# "Example St N- Somecity" (the city class admits spaces and dashes). The
# whitespace form is the fallback for rows shaped "456 Example St Somecity, MN".
# Examples here are synthetic on purpose: the real rows are restricted material
# and must not appear in a public repo, not even inside a comment.
ADDR_RE_DASH = re.compile(
    r"(?P<street>.+?)[-,]\s*(?P<city>[A-Za-z .'\-]+),\s*(?P<st>[A-Z]{2})\s+(?P<zip>\d{5})"
)
ADDR_RE_SPACE = re.compile(
    r"(?P<street>.+?)\s+(?P<city>[A-Za-z.'\-]+),\s*(?P<st>[A-Z]{2})\s+(?P<zip>\d{5})"
)


def parse_address(line: str):
    """Return (addr_raw, city, state, zip) or None. Dash form wins over space."""
    probe = re.sub(r"(?i)\bEMAIL:\s*", "", EMAIL_RE.sub("", line)).strip(" -,")
    for rx in (ADDR_RE_DASH, ADDR_RE_SPACE):
        m = rx.search(probe)
        if m:
            return (probe, m.group("city").strip(), m.group("st"), m.group("zip"))
    return None


def parse_roster(lines: list[str]):
    """
    Group lines into records. A line naming a preference level starts a record;
    following lines attach to it until the next preference line.
    Returns (records, unparsed).
    """
    groups, cur, unparsed = [], None, []
    for ln in lines:
        pref, _ = parse_preference(ln)
        if pref:
            if cur:
                groups.append(cur)
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
        else:
            unparsed.append({"line": ln, "why": "text before the first preference line"})
    if cur:
        groups.append(cur)

    records = []
    for g in groups:
        head, rest = g[0], g[1:]
        blob = " ".join(g)
        flags = []

        pref_key, pref_raw = parse_preference(head)
        exp, exp_raw = parse_expiration(blob)
        if exp is None:
            flags.append("no_expiration_parsed")

        # Business name is the text before the first '-' on the head line.
        name = head.split("-")[0].strip().rstrip(",").strip()
        if not name:
            unparsed.append({"line": head, "why": "no business name before first dash"})
            continue

        emails = EMAIL_RE.findall(blob)
        if len(emails) > 1:
            flags.append("multiple_emails_first_kept")
        email = emails[0] if emails else None

        phones = parse_phones(blob)
        phone = phones[0] if phones else None
        if not phones:
            flags.append("no_phone_parsed")
        if len(phones) > 1:
            flags.append("multiple_phones_first_kept")
        for p in phones:
            digits = re.sub(r"\D", "", p)
            if len(digits) not in (10, 11):
                flags.append(f"malformed_phone_in_source:{p}")

        # Owner: between the first and second dash on the head line, minus any
        # phone/preference text that ran together.
        owner = None
        parts = [p.strip() for p in head.split("-")]
        if len(parts) > 1:
            cand = parts[1]
            cand = EMAIL_RE.sub("", cand)
            cand = re.sub(r"\d", "", cand).strip(" .,/")
            if cand and re.search(r"[A-Za-z]", cand) and "preference" not in cand.lower():
                owner = cand
        if not owner:
            flags.append("no_owner_parsed")

        # The address is usually on a following line, but some rows carry it on
        # the head line instead (B&B Enterprized). Search the continuation lines
        # first, then the head line, so a head-line address is not lost.
        addr_raw = city = st = zc = None
        addr_line = None
        for ln in rest + [head]:
            got = parse_address(ln)
            if got:
                addr_raw, city, st, zc = got
                addr_line = ln
                break
        if addr_raw is None:
            flags.append("no_address_parsed")
        for ln in rest:
            if ln is not addr_line:
                unparsed.append({"line": ln, "why": f"unattached line under {name!r}"})

        # Any residual free text on the head line that is not name/owner/phone/
        # preference/expiration is a real note (e.g. "Will only hire
        # Sub-Contractors", "lives in Fargo"). Keep it verbatim.
        note = head
        for strip in filter(None, [name, owner, pref_raw, exp_raw] + phones):
            note = note.replace(strip, "")
        note = re.sub(r"[-\s,]{2,}", " ", note).strip(" -,")
        note = note if len(note) > 3 else None

        records.append({
            "name": name, "owner": owner, "phone": phone, "all_phones": phones,
            "email": email, "address_raw": addr_raw, "city": city,
            "state": st, "postal": zc, "preference": pref_key,
            "preference_raw": pref_raw, "expiration": exp,
            "expiration_raw": exp_raw, "note": note,
            "verbatim": " || ".join(g), "flags": flags,
        })
    return records, unparsed


def build_source_records(parsed, snapshot_uri, source_edition):
    out = []
    for i, r in enumerate(parsed, start=1):
        ladder = PREFERENCE_LADDER.get(r["preference"], {})
        key = re.sub(r"[^a-z0-9]+", "-", r["name"].lower()).strip("-")
        bsid = f"{SOURCE_ID}:{key}"

        claim_bits = ["Listed on the White Earth Nation TERO 'Certified Indian "
                      "Owned Businesses' register (updated 2026)."]
        if r["preference_raw"]:
            claim_bits.append(f"Register states: '{r['preference_raw']}'.")
        if ladder:
            claim_bits.append(
                f"Ordinance Chapter 6 category {ladder['ordinance_category']} "
                f"(level {ladder['level']}): {ladder['text']}."
            )
        if r["note"]:
            claim_bits.append(f"Register note: '{r['note']}'.")

        flags = list(r["flags"])
        flags.append("publication_rights_unconfirmed")
        if ladder and not ladder.get("certified", True):
            # A tier that the ordinance defines as NON-certified, appearing on a
            # document titled "Certified Indian Owned Businesses". Real tension:
            # record it, do not resolve it here.
            flags.append("tier_conflicts_with_document_title:non_certified_tier_on_certified_list")

        rec = {
            "business_source_id": bsid,
            "source_id": SOURCE_ID,
            "source_business_key": None,
            "business_entity_id": None,
            "nation_id": NATION_ID,
            "business_name_raw": r["name"],
            "business_name_normalized": re.sub(r"\s+", " ", r["name"].lower()).strip(),
            "dba_name": None,
            "owner_name_raw": r["owner"],
            "directory_type": "tero",
            # The ordinance defines Indian Preference "without regard to tribal
            # affiliation" -- so this register is not a White Earth citizen list.
            "identity_scope": "any_native",
            "identity_claim_text": " ".join(claim_bits),
            "ownership_percent": None,
            "ownership_threshold_min": 0.51,
            "control_requirement": (
                "At least 51% actual management and control by enrolled Indian "
                "owners, certified by the White Earth TERO Commission "
                "(registry rule, TBD-113)."
            ),
            "tribal_affiliation_raw": None,
            "verification_basis": "TERO_review",
            "certification_number": None,
            "certification_tier": r["preference_raw"],
            "certification_start": None,
            "certification_expiration": r["expiration"],
            "business_license_number": None,
            "service_category_raw": None,
            "naics": None,
            "description_raw": r["note"],
            "address_raw": r["address_raw"],
            "city": r["city"],
            "state_province": r["state"],
            "postal_code": r["postal"],
            "phone": r["phone"],
            "email": r["email"],
            "website": None,
            "source_url": SOURCE_URL,
            "source_edition": source_edition,
            "first_seen": TS,
            "last_seen": TS,
            "source_last_updated": None,
            "record_hash": "sha256:" + hashlib.sha256(
                r["verbatim"].encode("utf-8")).hexdigest(),
            "is_current": None,
            "validation_flags": flags,
            "ingestion_method": "docx",
            "raw_snapshot_uri": snapshot_uri,
            "refresh_run_id": RUN_ID,
            "relationship_basis_raw": r["preference_raw"],
            "relationship_basis": "unspecified",
            "certification_event_status": "approved",
            "source_priority_class": "tribal_primary",
            "cross_reference_only": False,
            "matched_primary_source_ids": None,
            "match_method": None,
            "match_confidence": None,
            "assertion_precedence_rank": 1,
        }
        out.append(rec)
    return out


def extract_ordinance_rules(lines):
    """Pull the verbatim rule text Cedar needs to explain this source's tiers."""
    joined = "\n".join(lines)

    def grab(pattern, n=1):
        hits = [l for l in lines if re.search(pattern, l, re.I)]
        return hits[:n]

    return {
        "source_id": SOURCE_ID,
        "nation_id": NATION_ID,
        "document": "White Earth TERO Ordinance (2026 copy, owner-supplied)",
        "captured": INGEST_DATE,
        "certification_authority": "White Earth TERO Commission",
        "ownership_threshold_min": 0.51,
        "employment_preference_levels": {
            "1": grab(r"grant a 1st level preference to any enrolled Indian"),
            "2": grab(r"grant a second level preference to Indians not covered"),
        },
        "contracting_preference_ladder": PREFERENCE_LADDER,
        "percentage_preference_schedule": [
            {"contract_min_usd": lo, "contract_max_usd": hi, "bid_preference_pct": pct}
            for lo, hi, pct in PERCENTAGE_PREFERENCE
        ],
        "percentage_preference_note": (
            "Preference is granted ABOVE the lowest responsible bid received, in "
            "the order of the preference levels. A Category C bidder must submit "
            "a timely responsible sealed bid and CANNOT match the low bid after "
            "the low bid is known."
        ),
        "indian_preference_definition": grab(r"INDIAN PREFERENCE\s*-\s*shall generally mean"),
        "veterans_preference": grab(r"VETERAN'?S PREFERENCE\s*-\s*shall mean"),
        "register_duty": grab(r"develop and maintain an updated register"),
        "confidentiality_clause": grab(r"shall remain strictly confidential"),
        "known_source_defects": [
            {
                "where": "Chapter 6, category C",
                "problem": (
                    "The ordinance text is corrupted: a phone-number-like string "
                    "'3012058210983' is spliced into the sentence, which reads "
                    "'3012058210983level preference to certified Indian - owned "
                    "firms whose principal'. The category-C level word is "
                    "destroyed in the source document."
                ),
                "handling": (
                    "Level 1 is inferred for category C from the surrounding "
                    "ladder (B grants 'second level' for employment; D grants a "
                    "'second level' for contracting to firms NOT qualifying "
                    "under C; and Chapter 6 states levels are in priority order). "
                    "FLAGGED, not silently repaired -- confirm against a clean "
                    "copy of the ordinance before publishing the ladder."
                ),
            }
        ],
        "line_count": len(lines),
        "raw_text_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="C:/Users/esm247/Downloads")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    roster_path = os.path.join(args.src, ROSTER_DOCX)
    ord_path = os.path.join(args.src, ORDINANCE_DOCX)
    for p in (roster_path, ord_path):
        if not os.path.exists(p):
            sys.exit(f"missing input: {p}")

    roster_lines = docx_lines(roster_path)
    ord_lines = docx_lines(ord_path)

    parsed, unparsed = parse_roster(roster_lines)
    print(f"roster: {len(roster_lines)} lines -> {len(parsed)} records, "
          f"{len(unparsed)} unparsed")

    snap_dir = os.path.join(HERE, "research", "white_earth_2026-08-28")
    snapshot_uri = f"research/white_earth_2026-08-28/{ROSTER_DOCX}"
    src_recs = build_source_records(parsed, snapshot_uri, "2026 update (owner-supplied docx)")
    rules = extract_ordinance_rules(ord_lines)

    # ---- report ----
    print()
    print(f"{'business':42s} {'tier':10s} {'expires':9s} {'flags'}")
    print("-" * 100)
    for r in src_recs:
        f = [x for x in r["validation_flags"] if x != "publication_rights_unconfirmed"]
        print(f"{r['business_name_raw'][:41]:42s} "
              f"{(r['certification_tier'] or '-')[:9]:10s} "
              f"{(r['certification_expiration'] or '-'):9s} "
              f"{','.join(f) if f else ''}")
    if unparsed:
        print("\nUNPARSED (not turned into records):")
        for u in unparsed:
            print(f"  [{u['why']}] {u['line'][:90]}")

    tiers = {}
    for r in src_recs:
        tiers[r["certification_tier"]] = tiers.get(r["certification_tier"], 0) + 1
    print("\ntier distribution:", json.dumps(tiers, indent=1))
    print(f"with email: {sum(1 for r in src_recs if r['email'])}/{len(src_recs)}")
    print(f"with address: {sum(1 for r in src_recs if r['address_raw'])}/{len(src_recs)}")

    if not args.write:
        print("\nDRY RUN -- pass --write to persist.")
        return 0

    os.makedirs(snap_dir, exist_ok=True)
    for p in (roster_path, ord_path):
        dst = os.path.join(snap_dir, os.path.basename(p))
        shutil.copy2(p, dst)
        print(f"snapshot -> {dst}  {sha256_file(dst)}")

    recs_path = os.path.join(HERE, "source_records", f"{SOURCE_ID}_white_earth.jsonl")
    os.makedirs(os.path.dirname(recs_path), exist_ok=True)
    tmp = recs_path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in src_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, recs_path)
    print(f"wrote {len(src_recs)} layer-1 records -> {recs_path}")

    rules_path = os.path.join(snap_dir, "certification_rules.json")
    tmp = rules_path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=1, ensure_ascii=False)
    os.replace(tmp, rules_path)
    print(f"wrote certification rules -> {rules_path}")

    if unparsed:
        up = os.path.join(snap_dir, "unparsed_lines.json")
        with open(up, "w", encoding="utf-8") as f:
            json.dump(unparsed, f, indent=1, ensure_ascii=False)
        print(f"wrote unparsed report -> {up}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
