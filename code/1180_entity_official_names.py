#!/usr/bin/env python3
"""
Cedar Press - 1180: `name` is the OFFICIAL name, taken from its source.

    py -3 code/1180_entity_official_names.py            # report, writes nothing
    py -3 code/1180_entity_official_names.py build
    py -3 code/1180_entity_official_names.py verify
    py -3 code/1180_entity_official_names.py selftest

WHY THIS EXISTS
---------------
Owner, 2026-09-04:

    "we dont need a canonical name we just need name and we have the sources
     listed for them"
    "name means official name - from federal register for tribes, DOI list for
     NHOs, that one website for ANCs and that other for native nonprofits then
     we can expand upon them"

`canonical_name` was a SHORT HANDLE, not a name. It equalled the official name
on only 26 of 577 BIA rows, and it had rotted: 21 handles had an identifying
word destroyed - `Benton` for the Utu Utu Gwaitu Paiute Tribe of the Benton
Paiute Reservation, `Nottawaseppi Potawatomi` with Huron deleted, and
`Confederated Yakama` for the Confederated Tribes and Bands of the Yakama
Nation.

Repairing those 21 by hand was the wrong fix, and it is worth saying why. A
handle Cedar maintains itself will rot again - the 16 splices cluster into
`Confederated <People>` and `<People> of <State>`, which is one bad shortening
rule, not sixteen typos. A name copied from the register that publishes it
cannot rot the same way, because the next capture simply overwrites it. So
`name` here is not repaired. It is SOURCED, and the source travels beside it
with its URL and capture date.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not invent a name. An entity whose class has no authoritative external
register - BIE schools, Native CDFIs, tribal colleges, intertribal
organizations - keeps the name Cedar already held and is marked
`name_source = cedar_internal`, so a reader can tell a sourced name from an
unsourced one at a glance. Hiding that distinction would make every name look
equally authoritative, which is the failure this whole exercise is correcting.

It does not delete `canonical_name`, and it does not edit the register. It
writes a table beside it. Dropping a column the site reads is a separate
decision, and it should be measurable against the old value first - which is
why `prior_canonical_name` and `name_differs_from_prior` ship in the output.

It does not adopt a name from a `cedar_only` or `*_only` reconciliation row.
Those name nothing on the other side, so there is no source to cite.

SOURCES, captured under data/source/official_names/ so a build is
reproducible without a network call:

    tribes, Alaska Native villages
        BIA, "Indian Entities Recognized by and Eligible To Receive Services
        From the United States Bureau of Indian Affairs", 91 FR 4102,
        2026-01-30, FR doc 2026-01899.  577 names.
    Native Hawaiian Organizations
        DOI Native Hawaiian Organization List, updated 2025-04-02.  189 orgs.
    ANCs
        ancsa.lbblawyers.com/native-corporations.htm.  194 corporations.
    Native nonprofits
        givenative.org - harvest in progress; wire in when the reconciliation
        lands, by adding one line to RECON_FILES.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source" / "official_names"
RECON = SRC / "reconciliation"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
OUT = ROOT / "data" / "spine" / "cedar_entity_names.csv"

csv.field_size_limit(10 ** 9)

#: source_id -> (label, url, capture_date). The URL and the date travel WITH
#: the name. A name whose provenance is a sentence in a commit message is not
#: sourced, it is remembered.
SOURCES = {
    "bia_federal_register": (
        "BIA, Indian Entities Recognized by and Eligible To Receive Services "
        "From the United States Bureau of Indian Affairs, 91 FR 4102",
        "https://www.federalregister.gov/documents/2026/01/30/2026-01899/"
        "indian-entities-recognized-by-and-eligible-to-receive-services-from-"
        "the-united-states-bureau-of",
        "2026-01-30"),
    "doi_nho_list": (
        "U.S. Department of the Interior, Native Hawaiian Organization List",
        "https://www.doi.gov/sites/default/files/documents/2025-04/"
        "nhol-complete-list-final-web.pdf",
        "2025-04-02"),
    "ancsa_lbb": (
        "Landye Bennett Blumstein LLP, ANCSA Regional and Village "
        "Corporations",
        "https://ancsa.lbblawyers.com/native-corporations.htm",
        "2026-09-04"),
    "givenative": (
        "GiveNative, Native nonprofit directory",
        "https://www.givenative.org/search?orgScope=on",
        "2026-09-04"),
    "cedar_internal": (
        "Cedar Press - no authoritative external register publishes a name "
        "for this entity class",
        "", ""),
}

#: WHY THERE IS NO match_type FILTER, which was my first and wrong design.
#:
#: Filtering to ("exact", "close") looked obviously right and produced 29 BIA
#: names out of 577. The selftest caught it because the Yakama row came back
#: None. The reason: `match_type` describes whether the SHORT HANDLE matched,
#: and the handle is not supposed to match - it is `Blackfeet` against
#: `Blackfeet Tribe of the Blackfeet Indian Reservation of Montana`. 548 rows
#: are `cedar_only` for that reason alone, and 547 of them still carry a
#: resolved `bia_name`, reached through the legal-name column:
#:
#:     464  federal_register_legal_name [exact]
#:      32  canonical_name [BIA name minus generic prefix]
#:      25  federal_register_legal_name [normalised]
#:      16  canonical_name [generic-word-stripped core name]
#:       9  federal_register_legal_name [BIA former name]
#:       1  federal_register_legal_name [generic-word-stripped core name]
#:
#: Every route ends at a string from the fetched register, which is the only
#: thing that matters here. The 9 reached through a BIA FORMER name are a
#: bonus: adopting the published name also retires the superseded spellings.
#:
#: So the test is simply: a cedar_uid on one side, a published name on the
#: other. `bia_only` / `doi_only` / `anc_only` rows carry no cedar_uid and are
#: excluded by that test without needing a special case.
TRUSTED = None  # kept as documentation of the rejected design

#: Order matters: the first source to claim a uid keeps it. The government
#: registers come first because a tribe that also appears in a nonprofit
#: directory is a tribe, and the BIA list is the stronger authority for it.
RECON_FILES = (
    ("bia_reconciliation.csv", "bia_name", "bia_federal_register"),
    ("nho_reconciliation.csv", "nho_name", "doi_nho_list"),
    ("anc_reconciliation.csv", "anc_name", "ancsa_lbb"),
)

#: Sources that live outside the reconciliation directory. The nonprofit links
#: are written by 1183 into data/spine/ because they are an identity artefact
#: (EIN -> cedar_uid), not a name reconciliation - but they carry the
#: GiveNative name, which IS the official name for those 359 entities.
EXTRA_SOURCES = (
    (ROOT / "data" / "spine" / "cedar_nonprofit_ein_links.csv", "name",
     "givenative"),
)


def _read(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def sourced_names():
    """cedar_uid -> (name, source_id), a per-source count, and collisions.

    A uid claimed by two sources keeps the first in RECON_FILES order and the
    clash is RETURNED rather than resolved quietly. An entity that is both a
    federally recognized tribe and an ANC would be a real finding about the
    entity, not a tie to break in silence.
    """
    picked, counts, collisions = {}, {}, []
    sources = [(RECON / f, c, s) for f, c, s in RECON_FILES]
    sources += [(p, c, s) for p, c, s in EXTRA_SOURCES]
    for path, namecol, source_id in sources:
        n = 0
        for row in _read(path):
            uid = (row.get("cedar_uid") or "").strip()
            name = (row.get(namecol) or "").strip()
            if not uid or not name:
                continue            # excludes every *_only row: no uid there
            route = ""
            note = row.get("note") or ""
            if "resolved via " in note:
                route = note.split("resolved via ", 1)[1].split(";")[0].strip()
            elif (row.get("match_type") or "").strip():
                route = "canonical_name [%s]" % row["match_type"].strip()
            if uid in picked:
                if picked[uid][0] != name:
                    collisions.append((uid, picked[uid], (name, source_id)))
                continue
            picked[uid] = (name, source_id, route)
            n += 1
        counts[source_id] = n
    return picked, counts, collisions


def build(apply: bool = False) -> int:
    reg = _read(REGISTER)
    if not reg:
        print("  register not found: %s" % REGISTER)
        return 1
    picked, counts, collisions = sourced_names()

    rows, changed, unsourced = [], 0, 0
    by_class = {}
    for r in reg:
        uid = (r.get("cedar_uid") or "").strip()
        held = (r.get("canonical_name") or "").strip()
        cls = (r.get("entity_class") or "").strip()
        name, source_id, route = picked.get(
            uid, (held, "cedar_internal", "no external register for this class"))
        if not name:
            name, source_id, route = held, "cedar_internal", "no published name found"
        label, url, captured = SOURCES[source_id]
        if source_id == "cedar_internal":
            unsourced += 1
        elif name != held:
            changed += 1
        slot = by_class.setdefault(cls, [0, 0])
        slot[0] += 1
        if source_id != "cedar_internal":
            slot[1] += 1
        rows.append({"cedar_uid": uid,
                     "name": name,
                     "entity_class": cls,
                     "name_source": source_id,
                     "name_source_label": label,
                     "name_source_url": url,
                     "name_captured": captured,
                     "name_match_route": route,
                     "prior_canonical_name": held,
                     "name_differs_from_prior": "1" if name != held else "0"})

    print("  1180 entity official names   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    register rows      : %d" % len(rows))
    for _, _, sid in list(RECON_FILES) + [(None, None, s) for _, _, s in EXTRA_SOURCES]:
        print("    from %-24s %d" % (sid, counts.get(sid, 0)))
    print("    unsourced (kept)   : %d" % unsourced)
    print("    name CHANGED       : %d" % changed)
    if collisions:
        print("    !! %d uid(s) claimed by two sources:" % len(collisions))
        for uid, a, b in collisions[:5]:
            print("       %s  %r(%s) vs %r(%s)" % (uid, a[0], a[1], b[0], b[1]))
    print()
    print("    %-46s %6s %8s" % ("entity_class", "rows", "sourced"))
    for cls, (tot, src) in sorted(by_class.items(), key=lambda kv: -kv[1][0]):
        print("    %-46s %6d %8d" % (cls[:46] or "(blank)", tot, src))

    if apply:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print()
        print("    wrote %s" % OUT.relative_to(ROOT))
    return 0


def verify() -> int:
    rows = _read(OUT)
    if not rows:
        print("  NOT BUILT: %s" % OUT)
        return 1
    blank = [r for r in rows if not (r.get("name") or "").strip()]
    unknown = [r for r in rows if r.get("name_source") not in SOURCES]
    sourced = sum(1 for r in rows if r.get("name_source") != "cedar_internal")
    changed = sum(1 for r in rows if r.get("name_differs_from_prior") == "1")
    print("  rows                 : %d" % len(rows))
    print("  blank name           : %d" % len(blank))
    print("  unknown source id    : %d" % len(unknown))
    print("  sourced              : %d (%.1f%%)"
          % (sourced, 100.0 * sourced / len(rows)))
    print("  differs from handle  : %d" % changed)
    if blank or unknown:
        print("  FAIL")
        return 1
    print("  OK")
    return 0


def selftest() -> int:
    """Every non-internal source must cite a URL, and the corrupt handles the
    owner complained about must actually be corrected by this build."""
    ok = True
    for sid, (_, url, _) in SOURCES.items():
        if sid != "cedar_internal" and not url.startswith("https://"):
            print("  FAIL %s carries no URL" % sid)
            ok = False
    picked, _, collisions = sourced_names()
    if not picked:
        print("  FAIL no reconciliation rows were read")
        ok = False
    # The named regression: the Yakama row must come out fully spelled.
    # The named regressions: three handles the owner or the audit called out.
    # Each asserts the SPECIFIC repair, not merely that something changed.
    for uid, must in (("CE-001CC-8N", "Confederated Tribes and Bands of the Yakama Nation"),
                      ("CE-001C0-09", "Benton Paiute Reservation"),
                      ("CE-0017R-QH", "Huron")):
        got = picked.get(uid)
        if not got or must not in got[0]:
            print("  FAIL %s did not resolve to a name containing %r: %r"
                  % (uid, must, got[0] if got else None))
            ok = False
        else:
            print("  %s -> %r  [%s]" % (uid, got[0], got[2]))
    print("  selftest %s  (%d sourced uids, %d collisions)"
          % ("PASS" if ok else "FAIL", len(picked), len(collisions)))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "build":
        raise SystemExit(build(apply=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(build(apply=False))
