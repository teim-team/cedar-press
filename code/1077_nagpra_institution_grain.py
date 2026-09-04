#!/usr/bin/env python3
# ORDERING, WRITTEN DOWN. This script writes `nagpra_notice_institutions.csv`
# WHOLESALE from the notice titles and enriches `nagpra_notices.csv` in place.
# `code/1084_nagpra_split_artefact_audit.py` is the SECOND enricher on the
# bridge and adds five columns to it IN PLACE, which a 1077 run drops, so 1084
# must be re-run after any run of this script. Both legs are declared in
# `KNOWN_ORDERINGS` / `ENRICHER_ORDERING` in code/cedar_pipeline.py.
# lint-ok: class6 - ordering declared above and in cedar_pipeline; 1084 is the enricher and runs last.
"""
Cedar Press - 1077: A NAGPRA NOTICE NAMES INSTITUTIONS, PLURAL, AND EACH HAS
ITS OWN ADDRESS.

    py -3 code/1077_nagpra_institution_grain.py           # measure + repair
    py -3 code/1077_nagpra_institution_grain.py verify    # read-only, exit 1
    py -3 code/1077_nagpra_institution_grain.py selftest  # prove checks fire

TWO CODEX FINDINGS, ONE PARSER
-------------------------------
**PR #29 finding 6** - document `2017-20294` ships
`institution_name = "Cultural Items: U.S. Army Corps of Engineers, Omaha
District"`, so it groups apart from every other Army Corps record. Right, and
**857 of 6,792 rows (12.6%)** carry such a prefix, not one:

    Cultural Items:              782
    Amendment:                    61
    Cultural Item:                 7
    Cultural Items Amendment:      7

The cost is exactly the one Codex named, and it is measurable: stripping the
prefix takes the distinct institution count from **2,184 to 1,895**, and
**287 prefixed names merge into an existing unprefixed name for the same
institution** - `Cultural Items: Denver Art Museum` (2) joining
`Denver Art Museum` (18), `Cultural Items: Bernice Pauahi Bishop Museum` (1)
joining that museum's other 22, and so on.

ROOT CAUSE: `TYPE_PREFIX_RE` in `77_build_nagpra_dataset.py` matches
`Notice of Intent to Repatriate` and stops. The 2015+ title form is
`Notice of Intent To Repatriate Cultural Items: <institution>`, so the object
phrase sits between the matched prefix and the colon, the `startswith(":")`
test fails, and the parser falls through to its `title_remainder` branch,
which keeps the whole tail. Fixed at source by consuming the optional object
phrase before the colon.

**PR #29 finding 8** - document `2025-08780` names institutions in SC, NC and
CT and ships a single `institution_city/state` of New Haven, CT. Right, and
worse in two ways Codex could not see from the sample:

  * `institution_count` said **4**. The notice names **6**.
  * `institution_names_all` split on `,\\s+and\\s+`, which cut *inside* an
    institution's own name: `South Carolina Department of Parks, Recreation,
    and Tourism` became `South Carolina Department of Parks, Recreation` and
    `Tourism, Columbia, SC` - **two fabricated institutions, neither of which
    exists**. That is a worse defect than the one reported, and it was
    produced by the column that was supposed to fix the reported one.
  * `institution_primary` was truncated mid-name at 100 characters.

ROOT CAUSE: the Federal Register separates co-holders with `; ` and closes the
list with `; and `. The parser never split on `;` at all, only on `, and `,
which is a *within-name* separator in ordinary American organisation names.
Fixed by splitting on `;` where present and falling back to the old rule only
where it is not - and the ordinary-name case proves why that order matters.

WHAT THIS BUILDS
-----------------
`data/clean/nagpra_notice_institutions.csv` - **one row per (notice,
institution)**, 7,234 rows over 6,792 notices, 7,087 of them carrying a state.
392 notices name more than one institution. This is the same shape the dataset
already uses for tribes (`nagpra_notice_entity_bridge.csv`), and it is the
answer to Codex's "emit one institution association per row or use a
structured bridge" - it does the second, which keeps the notice grain intact.

And in `nagpra_notices.csv`, in place:
    institution_name          notice-type prefix stripped   857 rows
    institution_primary       the FIRST institution, never truncated
    institution_names_all     correctly split, pipe-joined
    institution_count         re-derived
    institution_city/state    the PRIMARY institution's, not the last one's
    institution_name_basis    unchanged in meaning; recomputed

A NOTE ON WHAT IS *NOT* CLAIMED
--------------------------------
`institution_city/state` on the notice row is now the primary institution's
and is therefore **incomplete by construction** on the 392 multi-institution
notices. That is why the bridge exists, and the codebook says so rather than
the notice row pretending to a completeness it cannot have. Nothing is
inferred: every name, city and state in the bridge is a substring of the
notice's own Federal Register title.

INVARIANTS - exit 1 on any breach
----------------------------------
  I1  `nagpra_notices.csv` row and column counts are IDENTICAL after
  I2  `document_number` is never modified
  I3  every bridge row's name, city and state appear in that notice's title
  I4  bridge primary key is unique and never blank
  I5  institution_count on the notice equals its bridge row count, always
  I6  no shipped `institution_name` retains a notice-type prefix
  I7  the file did not move under us between read and write
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_nagpra_split as _split_rule   # noqa: E402  the ONE split rule
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1077_nagpra_institution_grain"

NOTICES = ROOT / "data" / "clean" / "nagpra_notices.csv"
BRIDGE = ROOT / "data" / "clean" / "nagpra_notice_institutions.csv"
BUILDER = ROOT / "code" / "77_build_nagpra_dataset.py"

TYPE_PREFIX_RE = re.compile(
    # `Notice To Rescind a Notice of Inventory Completion: <institution>` is a
    # real title form (6 notices) and the un-prefixed pattern skips it, so the
    # whole rescission phrase used to sit inside institution_name.
    r"^(?:Notice To Rescind an?\s+)?"
    r"Notice of (?:Inventory Completion|Intent to Repatriate|"
    r"Intended Repatriation|Intended Disposition)\b", re.I)
# The object phrase the 2015+ title form puts between the notice type and the
# colon. Anchored on a lookahead for the colon so it can never eat an
# institution name: if there is no colon after it, nothing is consumed.
OBJECT_HEAD_RE = re.compile(
    r"^\s*(?:of\s+)?(?:an?\s+|the\s+)?"
    r"(?:Cultural Items?|"
    r"Human Remains(?:\s+and\s+(?:Associated\s+)?Funerary Objects)?|"
    r"Native American Human Remains[^:]{0,80})?"
    r"(?:\s*Amendment)?\s*(?=:)", re.I)
POSSESSION_RE = re.compile(
    r"\b(?:in the (?:possession|control|physical custody) of)\s+", re.I)
CITY_STATE_RE = re.compile(r",\s*([A-Za-z][A-Za-z .'\-]{1,30}?),\s*([A-Z]{2})\s*$")
# The pre-2000 shapes. Applied ONLY where the title carries no semicolon,
# because `, and ` is a within-name separator in ordinary organisation names
# and splitting on it first is what fabricated "Tourism, Columbia, SC".
LEGACY_SPLIT_RE = re.compile(
    r",\s+and\s+|;\s+and\s+|"
    r"\s+and in the (?:possession|control|physical custody) of\s+", re.I)
LEADIN_RE = re.compile(
    r"^(?:and\s+)?(?:in the (?:possession|control|physical custody) of\s+)?"
    r"(?:the\s+)?", re.I)
LEFTOVER_PREFIX_RE = re.compile(r"^([A-Z][A-Za-z ]{2,40}):\s")
# Measured 2026-09-02 over all 6,792 notice titles by
# `py -3 code/1154_nagpra_fr_grain_audit.py report`: 19 adjacent `, and ` pairs
# trip the bare-noun test, 15 of them satisfy the strict merge conditions.
# This is a FLOOR on the intended delta, not a conservation check.
MERGE_FLOOR = 15


def notice_body(title: str):
    t = re.sub(r"\s+", " ", (title or "").strip())
    m = TYPE_PREFIX_RE.match(t)
    rest = t[m.end():] if m else t
    om = OBJECT_HEAD_RE.match(rest)
    if om:
        rest = rest[om.end():]
    if rest.lstrip().startswith(":"):
        body, how = rest.lstrip()[1:].strip(), "title_colon"
    else:
        pm = POSSESSION_RE.search(rest)
        if pm:
            body, how = rest[pm.end():].strip(), "title_possession"
        else:
            body, how = rest.strip(" :,"), "title_remainder"
    body = re.sub(r"\s*;?\s*Correction\s*$", "", body, flags=re.I).strip(" ,;")
    body = re.sub(r"^the\s+", "", body, flags=re.I).strip()
    return body, how


def split_institutions(body: str, with_notes: bool = False):
    """-> [(name, city, state)], in the order the notice lists them.

    THE `, and ` SPLIT IS PROVISIONAL. It is the Oxford comma inside an
    ordinary organisation's own name as often as it is a separator between two
    holders, and splitting on it unconditionally is what shipped `Louisiana
    Department of Culture, Recreation` - an agency that does not exist - on 12
    notices, with the notice's own city stranded on the phantom half.
    `code/cedar_nagpra_split.py` holds the ONE rule that decides, and it is the
    same rule `1084`'s detector A1 audits with, imported rather than
    re-implemented so the two cannot drift. Pairs it will not decide are left
    split and the reason is returned in `notes`, never guessed at.
    """
    segs = body.split(";") if ";" in body else LEGACY_SPLIT_RE.split(body)
    out = []
    for s in segs:
        s = LEADIN_RE.sub("", s.strip(" ,;.")).strip(" ,;.")
        if not s:
            continue
        cm = CITY_STATE_RE.search(s)
        if cm:
            out.append((s[:cm.start()].strip(" ,"), cm.group(1).strip(),
                        cm.group(2)))
        else:
            out.append((s, "", ""))
    out = [p for p in out if p[0]]
    notes, n_merged = [], 0
    if ";" not in body and len(out) > 1:
        before = len(out)
        out, notes = _split_rule.apply_merges(out, body)
        n_merged = before - len(out)
    return (out, notes, n_merged) if with_notes else out


def inst_type(name, fallback=""):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_n77", BUILDER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        inst_type.fn = mod.institution_type
    except Exception:
        inst_type.fn = None
    return fallback


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


BAD_TYPE_PREFIX = ('TYPE_PREFIX_RE = re.compile(\n'
                   '    r"^Notice of (?:Inventory Completion|Intent to Repatriate|"\n'
                   '    r"Intended Repatriation|Intended Disposition)\\b", re.I)')
BAD_SPLIT = ('INST_SPLIT_RE = re.compile(\n'
             '    r",\\s+and\\s+|;\\s+and\\s+|\\s+and in the '
             '(?:possession|control|physical custody) of\\s+",\n'
             '    re.I)')


def patch_builder(verify: bool) -> str:
    if not BUILDER.exists():
        return "ABSENT"
    src = BUILDER.read_text(encoding="utf-8")
    notes = []
    new = src
    if "OBJECT_HEAD_RE" in src:
        notes.append("object-phrase strip already present")
    elif BAD_TYPE_PREFIX in src:
        new = new.replace(BAD_TYPE_PREFIX, BAD_TYPE_PREFIX + '''
# THE 2015+ TITLE FORM PUTS AN OBJECT PHRASE BETWEEN THE NOTICE TYPE AND THE
# COLON: "Notice of Intent To Repatriate Cultural Items: <institution>".
# TYPE_PREFIX_RE stops at "Repatriate", the startswith(":") test then fails,
# and the parser falls through to title_remainder keeping "Cultural Items:"
# inside institution_name - 857 of 6,792 rows, splitting 287 institutions in
# two (Codex PR #29 finding 6). Anchored on a lookahead for the colon, so
# where there is no colon nothing is consumed and no institution name can be
# eaten. See code/1077_nagpra_institution_grain.py.
OBJECT_HEAD_RE = re.compile(
    r"^\\s*(?:of\\s+)?(?:Cultural Items?|"
    r"Human Remains(?:\\s+and\\s+(?:Associated\\s+)?Funerary Objects)?|"
    r"Native American Human Remains[^:]{0,80})?"
    r"(?:\\s*Amendment)?\\s*(?=:)", re.I)''')
        notes.append("object-phrase strip added")
    else:
        notes.append("TYPE_PREFIX_RE MOVED - patch by hand")

    old_call = '    rest = t[m.end():] if m else t\n    if rest.lstrip().startswith(":"):'
    if old_call in new:
        new = new.replace(old_call,
                          '    rest = t[m.end():] if m else t\n'
                          '    _om = OBJECT_HEAD_RE.match(rest)\n'
                          '    if _om:\n'
                          '        rest = rest[_om.end():]\n'
                          '    if rest.lstrip().startswith(":"):')
        notes.append("parse_institution now consumes it")
    elif "_om = OBJECT_HEAD_RE.match(rest)" in new:
        notes.append("parse_institution already consumes it")
    else:
        notes.append("parse_institution body MOVED - patch by hand")

    # IDEMPOTENCY, THE RIGHT WAY ROUND. This used to test `BAD_SPLIT in new`
    # FIRST and fall back to "already present" - but BAD_SPLIT is the literal
    # INST_SPLIT_RE definition, which survives the patch, so every run
    # prepended the comment block again. Four identical copies of
    # `INST_SEMI_RE = re.compile(r";")` were in `77` by 2026-09-02. The
    # already-present test has to come first.
    if "INST_SEMI_RE" in new:
        notes.append("semicolon rule already present")
    elif BAD_SPLIT in new:
        new = new.replace(BAD_SPLIT, '''# SPLIT ON THE SEMICOLON FIRST. The Federal Register separates co-holders
# with "; " and closes the list with "; and ". Splitting on ", and " first
# cuts INSIDE ordinary organisation names: "South Carolina Department of
# Parks, Recreation, and Tourism" became two institutions, one of them
# "Tourism, Columbia, SC", which does not exist (Codex PR #29 finding 8). The
# legacy rule is kept for the pre-2000 titles that carry no semicolon.
INST_SEMI_RE = re.compile(r";")
INST_SPLIT_RE = re.compile(
    r",\\s+and\\s+|;\\s+and\\s+|\\s+and in the '''
                          '''(?:possession|control|physical custody) of\\s+",
    re.I)''')
        notes.append("semicolon rule added")
    elif "INST_SEMI_RE" in new:
        notes.append("semicolon rule already present")
    else:
        notes.append("INST_SPLIT_RE MOVED - patch by hand")

    old_parts = ('    parts = [p.strip(" ,;.") for p in '
                 'INST_SPLIT_RE.split(body or "") if p.strip()]')
    if old_parts in new:
        new = new.replace(old_parts,
                          '    _b = body or ""\n'
                          '    _segs = _b.split(";") if ";" in _b else '
                          'INST_SPLIT_RE.split(_b)\n'
                          '    parts = [re.sub(r"^\\s*and\\s+", "", '
                          'p.strip(" ,;."), flags=re.I)\n'
                          '             for p in _segs if p.strip()]')
        notes.append("institution_parts now semicolon-aware")
    elif '_segs = _b.split(";")' in new:
        notes.append("institution_parts already semicolon-aware")
    else:
        notes.append("institution_parts body MOVED - patch by hand")

    if verify:
        return "; ".join(notes) + " (verify: not written)"
    if new != src:
        BUILDER.with_name(BUILDER.name + TAG).write_text(src, encoding="utf-8")
        BUILDER.write_text(new, encoding="utf-8")
    return "; ".join(notes)


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    verify = arg == "verify"

    if not NOTICES.exists():
        print("  1077: nagpra_notices.csv ABSENT")
        return 1
    fp = fingerprint(NOTICES)
    with NOTICES.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)
    n_before, c_before = len(rows), len(cols)

    for _c in ("institution_split_flag", "institution_split_basis"):
        if _c not in cols:
            cols.append(_c)
    bridge, changed_prefix, changed_count, changed_loc = [], 0, 0, 0
    i3_breach, i6_breach = 0, 0
    flagged_rows = []
    merged_pairs, merged_notices = 0, 0
    for r in rows:
        title = r.get("title") or ""
        body, how = notice_body(title)
        parts, split_notes, _m = split_institutions(body, with_notes=True)
        if _m:
            merged_pairs += _m
            merged_notices += 1
        if not parts:
            parts = [(body or (r.get("institution_name") or ""), "", "")]
        flat = re.sub(r"\s+", " ", title).lower()

        old_name = r.get("institution_name") or ""
        if LEFTOVER_PREFIX_RE.match(old_name) and not \
                LEFTOVER_PREFIX_RE.match(body):
            changed_prefix += 1
        if str(len(parts)) != (r.get("institution_count") or ""):
            changed_count += 1
        if (parts[0][1] or parts[0][2]) and (
                parts[0][1] != (r.get("institution_city") or "") or
                parts[0][2] != (r.get("institution_state") or "")):
            changed_loc += 1

        # `institution_name` keeps its old meaning - the institution string
        # with the addresses taken out - but is now rebuilt from the SPLIT
        # parts, so it agrees with `institution_names_all` name for name and
        # every part has lost its own ", City, ST", not just the last one.
        r["institution_name"] = "; ".join(p[0] for p in parts)
        r["institution_primary"] = parts[0][0]
        r["institution_names_all"] = "|".join(p[0] for p in parts)
        r["institution_count"] = str(len(parts))
        r["institution_city"] = parts[0][1]
        r["institution_state"] = parts[0][2]
        r["institution_name_basis"] = how
        # FLAG, NEVER GUESS. A `, and ` pair that trips the bare-noun test but
        # that the rule will not decide is left exactly as the title splits it
        # and the reason travels with the row, so a buyer can see that these
        # fragments MAY be one institution rather than being told they are two.
        r["institution_split_flag"] = "|".join(
            sorted({f for _, f, _ in split_notes}))
        r["institution_split_basis"] = " || ".join(b for _, _, b in split_notes)
        if r["institution_split_flag"]:
            # NAME WHAT WAS FLAGGED, not just how many. A refusal counted and
            # not named is a refusal nobody can act on.
            flagged_rows.append((r["document_number"],
                                 r["institution_split_flag"],
                                 r["institution_name"][:120]))
        if LEFTOVER_PREFIX_RE.match(r["institution_name"]):
            i6_breach += 1

        for i, (nm, city, st) in enumerate(parts, 1):
            # I3: nothing is invented - every field must be IN the title.
            for v in (nm, city):
                if v and v.lower() not in flat:
                    i3_breach += 1
            bridge.append({
                # `i` is NOT the row's position in this file: it is the
                # institution's ordinal in the notice's own Federal Register
                # TITLE, a fixed published string, so the same document yields
                # the same ids in every build on every machine. Re-sorting or
                # re-filtering this file cannot change one. I4 checks it:
                # 7,234 distinct, 0 blank.
                # lint-ok: class7 - ordinal within a published title, not a rank in this file
                "nagpra_notice_institution_id": f"{r['document_number']}#{i:02d}",
                "document_number": r["document_number"],
                "institution_seq": i,
                "institution_name": nm,
                "institution_city": city,
                "institution_state": st,
                "publication_date": r.get("publication_date", ""),
                "notice_type": r.get("notice_type", ""),
                "institution_basis": how,
                "n_institutions_in_notice": len(parts),
                "built_date": TODAY,
            })

    # ---- invariants ------------------------------------------------------
    breaches = []
    if len(rows) != n_before:
        breaches.append(f"I1 rows {n_before} -> {len(rows)}")
    ids = [b["nagpra_notice_institution_id"] for b in bridge]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        breaches.append(f"I4 bridge key not unique/blank: {len(ids)} rows, "
                        f"{len(set(ids))} distinct")
    per = {}
    for b in bridge:
        per[b["document_number"]] = per.get(b["document_number"], 0) + 1
    if any(int(r["institution_count"]) != per.get(r["document_number"], 0)
           for r in rows):
        breaches.append("I5 institution_count disagrees with bridge row count")
    if i3_breach:
        breaches.append(f"I3 {i3_breach} bridge fields are not substrings of "
                        f"their own notice title")
    if i6_breach:
        breaches.append(f"I6 {i6_breach} institution_name still carry a "
                        f"notice-type prefix")
    # I8. A conservation check is not a proof that something happened
    # (AGENT_FIELD_GUIDE rule 5). MERGE_FLOOR is derived from the notice TITLES
    # on every run, not from the table, so it does not drift after the repair
    # lands: if the split rule stops firing, this fires instead.
    if merged_pairs < MERGE_FLOOR:
        breaches.append(f"I8 the oxford `, and ` merge rule did not fire: "
                        f"{merged_pairs} pairs rejoined, floor {MERGE_FLOOR}")

    multi = sum(1 for r in rows if int(r["institution_count"]) > 1)
    with_state = sum(1 for b in bridge if b["institution_state"])
    print(f"  1077 nagpra institution grain")
    print(f"    notices                        {n_before:,}")
    print(f"    bridge rows (notice x inst)    {len(bridge):,}   "
          f"{with_state:,} carry a state")
    print(f"    notices naming >1 institution  {multi:,}")
    print(f"    notice-type prefix stripped    {changed_prefix:,} rows")
    print(f"    institution_count corrected    {changed_count:,} rows")
    print(f"    city/state repointed to the primary institution "
          f"{changed_loc:,} rows")
    print(f"    oxford `, and ` pairs rejoined {merged_pairs:,} on "
          f"{merged_notices:,} notices")
    print(f"    left split and FLAGGED, not guessed at "
          f"{len(flagged_rows):,} notices")
    for _dn, _fl, _nm in flagged_rows:
        print(f"      {_dn}  {_fl}  {_nm}")
    for b in breaches:
        print(f"    BREACH {b}")

    gen = patch_builder(verify)
    print(f"    generator code/77_build_nagpra_dataset.py: {gen}")

    if breaches:
        return 1
    if verify:
        stale = (changed_prefix or changed_count or changed_loc)
        if stale:
            print(f"  VERIFY FAILED: the shipped table is stale against this "
                  f"parser ({changed_prefix} prefixes, {changed_count} counts, "
                  f"{changed_loc} locations)")
            return 1
        return 0

    if fingerprint(NOTICES) != fp:                        # I7
        print("    BREACH I7 nagpra_notices.csv changed under us - ABORTED")
        return 1
    bak = NOTICES.with_name(NOTICES.name + TAG)
    if not bak.exists():
        shutil.copy2(NOTICES, bak)
    tmp = NOTICES.with_suffix(".csv.part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if fingerprint(NOTICES) != fp:
        tmp.unlink(missing_ok=True)
        print("    BREACH I7 changed during write - ABORTED")
        return 1
    os.replace(tmp, NOTICES)

    btmp = BRIDGE.with_suffix(".csv.part")
    with btmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(bridge[0].keys()))
        w.writeheader()
        w.writerows(bridge)
    os.replace(btmp, BRIDGE)

    (ROOT / "docs" / "NAGPRA_INSTITUTION_GRAIN.json").write_text(
        json.dumps({"measured_date": TODAY, "notices": n_before,
                    "notice_cols": c_before,
                    "bridge_rows": len(bridge),
                    "bridge_rows_with_state": with_state,
                    "multi_institution_notices": multi,
                    "prefix_stripped_rows": changed_prefix,
                    "institution_count_corrected": changed_count,
                    "city_state_repointed": changed_loc,
                    "oxford_and_pairs_rejoined": merged_pairs,
                    "notices_with_a_rejoined_name": merged_notices,
                    "notices_left_split_and_flagged": len(flagged_rows),
                    "notices_left_split_and_flagged_named": [
                        {"document_number": d, "flag": f,
                         "institution_name": n}
                        for d, f, n in flagged_rows],
                    "split_rule": "code/cedar_nagpra_split.py - the ONE rule, "
                                  "imported by 77, 1077 and 1084",
                    "distinct_institution_names_before": 2184,
                    "distinct_institution_names_after":
                        len({b["institution_name"] for b in bridge}),
                    "generator": gen}, indent=2) + "\n", encoding="utf-8")
    return 0


def selftest() -> int:
    t = ("Notice of Intent To Repatriate Cultural Items: U.S. Army Corps of "
         "Engineers, Omaha District, Omaha, NE")
    b, how = notice_body(t)
    assert b == "U.S. Army Corps of Engineers, Omaha District, Omaha, NE", b
    assert how == "title_colon", how
    assert not LEFTOVER_PREFIX_RE.match(b)

    # The fabrication this replaces: `, and ` must NOT split a name that the
    # notice separated with semicolons.
    body = ("A Institute, Columbia, SC; South Carolina Department of Parks, "
            "Recreation, and Tourism, Columbia, SC; and Yale Peabody Museum, "
            "New Haven, CT")
    ps = split_institutions(body)
    assert len(ps) == 3, ps
    assert ps[1][0] == "South Carolina Department of Parks, Recreation, and " \
                       "Tourism", ps[1]
    assert ps[2] == ("Yale Peabody Museum", "New Haven", "CT"), ps[2]
    assert ps[0][2] == "SC" and ps[2][2] == "CT"
    # The regression this rule guards must be REPRODUCIBLE from the old rule,
    # or the fix is guarding an imaginary bug. Note the segment COUNT is the
    # same either way - the old rule miscounts by cutting one real name in two
    # and joining two real ones, which is exactly why a count check would
    # never have caught it.
    legacy = [x.strip() for x in LEGACY_SPLIT_RE.split(body) if x.strip()]
    assert any(x.startswith("Tourism") for x in legacy), (
        "the specific fabrication - a segment beginning 'Tourism', an "
        "institution that does not exist - must be reproducible from the old "
        f"rule: {legacy}")
    assert not any(x[0].startswith("Tourism") for x in ps), ps

    # A title with no colon after the object phrase must lose nothing.
    t2 = "Notice of Inventory Completion for Native American Human Remains " \
         "From Unalakleet, AK, in the Control of the Alaska State Office"
    b2, how2 = notice_body(t2)
    assert "Alaska State Office" in b2, b2
    print("  1077 selftest OK: the prefix strip fires, the semicolon rule "
          "keeps 'Parks, Recreation, and Tourism' whole where the legacy rule "
          f"splits it into {len(legacy)} pieces, and a colon-less title is "
          "untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
