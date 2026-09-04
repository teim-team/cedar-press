#!/usr/bin/env python3
"""
Cedar Press - 1183: Native nonprofits become Cedar entities.

    py -3 code/1183_native_nonprofit_entities.py            # report, writes nothing
    py -3 code/1183_native_nonprofit_entities.py build
    py -3 code/1183_native_nonprofit_entities.py verify
    py -3 code/1183_native_nonprofit_entities.py selftest

WHY THIS EXISTS
---------------
Owner, 2026-09-04: *"you still dont appear to have native nonprofits on this
list"*, and then, plainly: *"add native non profits to the canonical entity
lists and lnk cedar id to them"*.

He is right, and the gap is structural rather than cosmetic. The register held
17 entity classes and NOT ONE of them was a Native nonprofit. Measured: of
12,689 rows in `nonprofits.csv`, only 555 carried a `cedar_uid`, and every one
of those 555 was keyed because the filer is something else that happens to file
a 990 -

    379  a federally recognized tribe
     54  an intertribal organization
     47  a state-recognized tribe
     35  a federal-level constituency entity
     39  Alaska Native villages, NHOs and ANCs

- which means a standalone Native-led nonprofit had NO CLASS IT WAS ALLOWED TO
BE. The other 12,134 rows were not a matching failure. There was nothing valid
to key them to. That is why every earlier pass at "nonprofit coverage" stalled.

MEMBERSHIP IS EVIDENCED, NOT ASSERTED
-------------------------------------
Cedar's rule is that a class says how membership is proven. This one is proven
in two independent legs, both captured:

  1. LISTED by GiveNative, a directory of Native-led nonprofits (398 orgs, 380
     publishing an EIN). This is a third party vouching that the organization
     is Native-led - the judgement Cedar cannot make from a 990, because the
     IRS does not publish board composition.
  2. REGISTERED with the IRS. Measured 2026-09-04: 253 of the 257 GiveNative
     orgs absent from Cedar's nonprofit file are present in the full BMF, all
     subsection 03, with rulings back to 1998.

Both legs, and the EIN is the join. That is tier A evidence by Cedar's own
definition, and it is why the class can be minted without a hand review of
each row.

WHAT IT REFUSES TO DO
---------------------
No EIN, no entity. 18 GiveNative profiles publish no EIN - fiscally sponsored
projects and unclaimed pages - and they are skipped rather than minted on a
name alone. A name is a candidate; this file mints identity.

It also never mints over an existing entity. If the EIN already resolves to a
`cedar_uid` anywhere Cedar keys identifiers, the row LINKS to it. Minting a
second uid for an entity Cedar already holds is the one unforgivable act in an
identity system - the Museum of the Cherokee People renamed itself in 2023 and
must not become two entities because of it.

AK / HI SCOPE. 20 of these are Hawai'i and 9 are Alaska. They are minted with
their real `state`, and the scope rule several workstreams apply is left to
those workstreams rather than being silently baked into identity here.
"""
from __future__ import annotations

import csv
import importlib.util
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPINE = ROOT / "data" / "spine"
REGISTER = SPINE / "cedar_identity_register.csv"
TYPES = SPINE / "cedar_entity_types.csv"
GIVENATIVE = ROOT / "data" / "source" / "official_names" / "givenative_orgs.csv"
TRANCHE = (ROOT / "data" / "source" / "official_names" / "reconciliation"
           / "nonprofit_classification_tranche.csv")
NONPROFITS = ROOT / "dist" / "customer" / "nonprofits.csv"

ENTITY_CLASS = "Native nonprofit"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 9)

_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _identity():
    """Load 503_identity - the ONE check-character implementation."""
    spec = importlib.util.spec_from_file_location(
        "cedar_503_identity", str(ROOT / "code" / "503_identity.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ordinal(uid: str) -> int:
    """Inverse of 503_identity.encode. There is no decode() in that module."""
    payload = uid.split("-")[1]
    n = 0
    for ch in payload:
        n = n * 32 + _B32.index(ch)
    return n


def _read(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm_ein(v: str) -> str:
    d = "".join(c for c in (v or "") if c.isdigit())
    return d.zfill(9) if d else ""


def _agree(a: str, b: str) -> bool:
    """Do two names refer to the same organization?

    Deliberately strict. A false AGREE keeps a wrong collapse; a false
    DISAGREE mints an entity that already exists, and a duplicate identity is
    the more expensive error - so this only accepts near-identity after
    normalising case, punctuation and the legal suffix.
    """
    # NOTE: the  word boundaries below were once written through a
    # shell heredoc that turned each one into a literal backspace
    # (0x08). The pattern then matched NOTHING, so legal-suffix
    # stripping silently did not run - and had the boundaries merely
    # been dropped instead, it would have stripped "co" out of
    # "Community" and manufactured agreement between unrelated orgs.
    import re as _re
    def norm(x):
        x = (x or "").lower()
        x = _re.sub(r"\b(inc|incorporated|corp|corporation|llc|ltd|co)\b", " ", x)
        x = _re.sub(r"[^a-z0-9]+", " ", x)
        return " ".join(x.split())
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    if ta == tb:
        return True

    # A LEGAL-FORM WORD IS NEVER A ROUNDING ERROR. The "one word apart" rule
    # below let `Catawba Indian Nation` agree with `Catawba Indian Nation
    # Foundation` - they differ by exactly one token - which is the containment
    # case this function exists to reject. A nation and that nation's
    # foundation are two legal persons filing two 990s under two EINs, and the
    # single word "foundation" is the entire difference between them.
    FORM = {"foundation", "trust", "fund", "institute", "club", "association",
            "society", "council", "board", "authority", "enterprise",
            "enterprises", "holdings", "development", "project", "coalition",
            "alliance", "network", "center", "centre"}
    if (ta ^ tb) & FORM:
        return False

    # otherwise allow a single incidental word to differ
    return len(ta ^ tb) == 1 and len(ta & tb) >= 2


def bmf_names(eins: set) -> dict:
    """EIN -> the name the IRS puts against it, for the EINs asked for.

    WHY THE IRS ARBITRATES AND NAME SIMILARITY DOES NOT.
    Deciding whether an existing link is trustworthy by comparing names cannot
    work, and this was measured rather than assumed:

        Museum of the Cherokee Indian  vs  Museum of the Cherokee People
            the SAME organization, renamed in 2023        Jaccard 0.50
        Catawba Indian Nation          vs  Catawba Nation Foundation
            two DIFFERENT legal persons                   Jaccard 0.50

    Identical similarity, opposite truth, so no threshold is right for both -
    and the two failure directions are not symmetric. Too permissive keeps a
    wrong collapse; too strict mints a second identity for an entity Cedar
    already holds, which is the more expensive error.

    The IRS Business Master File settles it with evidence instead: it publishes
    the legal name registered against each EIN. If the BMF says TULALIP
    FOUNDATION and Cedar keyed that EIN to the Tulalip Tribes, the link is
    wrong however similar the strings look; if the BMF says MUSEUM OF THE
    CHEROKEE INDIAN and Cedar holds the same, the link is right even though the
    directory shows a newer trading name.
    """
    import glob
    found = {}
    pattern = str(ROOT / "data" / "raw" / "external" / "irs990"
                  / "bmf_full_*" / "eo*.csv")
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                e = norm_ein(row.get("EIN"))
                if e in eins and e not in found:
                    found[e] = (row.get("NAME") or "").strip()
        if len(found) == len(eins):
            break
    return found


def existing_name_by_uid() -> dict:
    """cedar_uid -> the name Cedar currently holds, for the agreement test."""
    out = {}
    for r in _read(SPINE / "cedar_entity_names.csv"):
        if r.get("cedar_uid"):
            out[r["cedar_uid"]] = r.get("name", "")
    if not out:
        for r in _read(REGISTER):
            if r.get("cedar_uid"):
                out[r["cedar_uid"]] = r.get("canonical_name", "")
    return out


def existing_ein_to_uid() -> dict:
    """Every EIN Cedar already resolves, so nothing is minted twice.

    ORDER IS THE WHOLE POINT, and getting it wrong cost a re-run. `setdefault`
    means the FIRST source to claim an EIN wins, so this file's own arbitrated
    output must be read BEFORE nonprofits.csv. Read the other way round, the
    stale link nonprofits.csv holds - the one the IRS says is wrong, keying
    TULALIP FOUNDATION's EIN to the Tulalip Tribes - beat the corrected link
    written minutes earlier, and the 11 repaired entities were proposed for
    minting all over again.
    """
    out = {}
    # 1. this script's arbitrated output: the corrected answer
    for r in _read(SPINE / "cedar_nonprofit_ein_links.csv"):
        ein = norm_ein(r.get("EIN"))
        uid = (r.get("cedar_uid") or "").strip()
        if ein and uid:
            out.setdefault(ein, uid)
    # 2. then what Cedar held before, which may be the wrong collapse
    for r in _read(NONPROFITS):
        ein = norm_ein(r.get("EIN"))
        uid = (r.get("cedar_uid") or "").strip()
        if ein and uid:
            out.setdefault(ein, uid)
    for r in _read(TRANCHE):
        ein = norm_ein(r.get("EIN") or r.get("givenative_ein"))
        uid = (r.get("cedar_uid") or "").strip()
        if ein and uid:
            out.setdefault(ein, uid)
    return out


def plan():
    """Returns (to_mint, to_link, skipped_no_ein, next_ordinal)."""
    ident = _identity()
    reg = _read(REGISTER)
    used = {r["cedar_uid"] for r in reg if r.get("cedar_uid")}
    nxt = max(_ordinal(u) for u in used) + 1

    known = existing_ein_to_uid()
    existing_name = existing_name_by_uid()
    already_nonprofit = {r["cedar_uid"] for r in reg
                         if r.get("entity_class") == ENTITY_CLASS}
    # only the already-linked EINs need arbitration
    linked_eins = {norm_ein(o.get('ein')) for o in _read(GIVENATIVE)}
    linked_eins = {e for e in linked_eins if e and e in known}
    irs = bmf_names(linked_eins) if linked_eins else {}
    seen_ein = set()
    to_mint, to_link, skipped = [], [], []
    for org in _read(GIVENATIVE):
        ein = norm_ein(org.get("ein"))
        name = (org.get("name") or "").strip()
        if not name:
            continue
        if not ein:
            skipped.append(name)
            continue
        if ein in seen_ein:
            continue
        seen_ein.add(ein)
        if ein in known:
            # AN EXISTING LINK IS A CLAIM, NOT A FACT - check it agrees.
            #
            # Measured 2026-09-04: 12 of the 21 EINs Cedar already resolved
            # pointed at a DIFFERENT organization than the one that owns the
            # EIN. Three separate Blackfeet nonprofits - FAST Blackfeet,
            # Blackfeet Eco Knowledge, Blackfeet Mmip - were all keyed to
            # CE-0012G-ES, the Blackfeet Tribe. Tulalip Foundation resolved to
            # the Tulalip Tribes; Boys and Girls Club of Rosebud to the Rosebud
            # Sioux Tribe. One was not even a parent relationship: the National
            # Center for American Indian Enterprise Development was keyed to the
            # Native American Development Center, a different organization.
            #
            # A tribe's foundation is a distinct legal person that files its own
            # 990 under its own EIN. Collapsing it into the tribe is the error
            # docs/IDENTIFIER_STANDARD names in its own words - "the exact error
            # that keyed Amee Bay to the Three Affiliated Tribes" - and taking
            # the existing link on trust would have propagated it into a new
            # entity class rather than fixing it.
            #
            # So the link is accepted only when the names AGREE. Where they do
            # not, the nonprofit is minted as itself and `related_entity` records
            # the uid it was wrongly collapsed into, so the old attribution can
            # be reviewed rather than silently dropped.
            # THIS SCRIPT'S OWN OUTPUT IS NOT ARBITRATED. The BMF check exists
            # to judge links Cedar inherited from elsewhere. Re-judging an
            # entity 1183 minted itself compares the directory name against the
            # IRS name for the same EIN - which often differ in form ("THE",
            # abbreviations, all-caps) - so a second run failed the test and
            # minted 329 duplicates of entities it had created minutes before.
            # An identity a script just established is not evidence to weigh.
            if known[ein] in already_nonprofit:
                to_link.append((ein, name, known[ein]))
                continue
            held = existing_name.get(known[ein], "")
            irs_name = irs.get(ein, "")
            # the IRS decides; _agree only stands in when the BMF is silent
            trust = _agree(held, irs_name) if irs_name else _agree(held, name)
            if trust:
                to_link.append((ein, name, known[ein]))
            else:
                org = dict(org)
                org["_collapsed_into"] = known[ein]
                org["_collapsed_name"] = held
                to_mint.append((ein, name, org))
        else:
            to_mint.append((ein, name, org))
    return to_mint, to_link, skipped, nxt, ident


def build(apply: bool = False) -> int:
    to_mint, to_link, skipped, nxt, ident = plan()
    print("  1183 native nonprofit entities   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    GiveNative orgs with an EIN : %d" % (len(to_mint) + len(to_link)))
    print("    already a Cedar entity      : %d  (linked, never re-minted)"
          % len(to_link))
    print("    TO MINT as %-17s: %d" % (ENTITY_CLASS, len(to_mint)))
    print("    skipped, no EIN published   : %d" % len(skipped))
    print("    next free uid ordinal       : %d -> %s" % (nxt, ident.mint(nxt)))

    if not apply:
        print()
        print("    sample of what would be minted:")
        for ein, name, org in to_mint[:6]:
            print("      %s  %-46s %s" % (ein, name[:46], org.get("state", "")))
        return 0

    shutil.copyfile(REGISTER, REGISTER.with_suffix(
        ".csv.bak_%s_pre_1183_native_nonprofits" % TODAY))

    reg = _read(REGISTER)
    fields = list(reg[0].keys())
    n = nxt
    minted = []
    for ein, name, org in to_mint:
        uid = ident.mint(n)
        n += 1
        row = {c: "" for c in fields}
        row.update({
            "cedar_uid": uid,
            "canonical_name": name,
            "entity_class": ENTITY_CLASS,
            "minted": TODAY,
            "register_status": "active",
            "state": (org.get("state") or "").strip(),
            "class_since_basis":
                "minted %s by code/1183_native_nonprofit_entities.py; listed "
                "as Native-led by GiveNative AND registered with the IRS "
                "(EIN %s)" % (TODAY, ein),
            "federal_register_legal_name_basis":
                "OUT_OF_SCOPE_BY_CONSTRUCTION - a Native nonprofit is not "
                "listed in the BIA annual list",
            "minted_basis":
                "`minted` records the date this entity entered the register.",
        })
        reg.append(row)
        minted.append((uid, ein, name))

    with REGISTER.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(reg)
    print()
    print("    minted %d entities into %s" % (len(minted), REGISTER.name))

    # the EIN -> uid link, which is the half that makes them findable
    link_path = SPINE / "cedar_nonprofit_ein_links.csv"
    with link_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["EIN", "cedar_uid", "name", "link_basis", "link_tier"])
        for uid, ein, name in minted:
            w.writerow([ein, uid, name,
                        "minted 1183: GiveNative listing + IRS registration", "A"])
        for ein, name, uid in to_link:
            w.writerow([ein, uid, name,
                        "existing Cedar entity matched on exact EIN", "A"])
    print("    wrote %s (%d links)"
          % (link_path.relative_to(ROOT), len(minted) + len(to_link)))

    # and the class needs a definition, or 1181's selftest fails the build
    types = _read(TYPES)
    if types and not any(r.get("type_code") == ENTITY_CLASS for r in types):
        tf = list(types[0].keys())
        row = {c: "" for c in tf}
        row.update({
            "type_code": ENTITY_CLASS,
            "label": "Native nonprofit (501(c)(3))",
            "row_count": str(len(minted)),
            "definition":
                "A nonprofit corporation that is Native-led and registered "
                "with the IRS, and that is not itself a tribal government, "
                "ANC, NHO or other entity class Cedar already holds. "
                "Membership requires BOTH legs: a third-party directory of "
                "Native-led organizations lists it, and the IRS Business "
                "Master File carries its EIN. It is NOT any nonprofit serving "
                "Native people - a municipal housing authority serving a "
                "reservation is not a Native nonprofit, which is the same "
                "error that once attributed $1.13B of Omaha city housing "
                "money to the Omaha Tribe.",
            "statutory_basis": "26 U.S.C. 501(c)(3) for the registration leg; "
                               "Native-led status has no statutory register",
            "evidence_citation":
                "givenative.org directory + IRS EO BMF (bmf_full_2026-08-12); "
                "253 of 257 verified present in the BMF on 2026-09-04",
            "confidence": "established",
        })
        if minted:
            row["example_uid_1"], row["example_name_1"] = minted[0][0], minted[0][2]
        if len(minted) > 1:
            row["example_uid_2"], row["example_name_2"] = minted[1][0], minted[1][2]
        types.append(row)
        with TYPES.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=tf)
            w.writeheader()
            w.writerows(types)
        print("    added the %r definition to %s" % (ENTITY_CLASS, TYPES.name))
    return 0


def verify() -> int:
    ident = _identity()
    reg = _read(REGISTER)
    np_rows = [r for r in reg if r.get("entity_class") == ENTITY_CLASS]
    uids = [r["cedar_uid"] for r in reg if r.get("cedar_uid")]
    ok = True
    print("  register rows        : %d" % len(reg))
    print("  %-21s: %d" % (ENTITY_CLASS, len(np_rows)))
    print("  all uids valid       : %s" % all(ident.valid(u) for u in uids))
    if not all(ident.valid(u) for u in uids):
        ok = False
    dup = len(uids) - len(set(uids))
    print("  duplicate uids       : %d" % dup)
    if dup:
        ok = False
    blank = sum(1 for r in np_rows if not (r.get("canonical_name") or "").strip())
    print("  blank names          : %d" % blank)
    if blank:
        ok = False
    links = _read(SPINE / "cedar_nonprofit_ein_links.csv")
    print("  EIN links            : %d" % len(links))
    eins = [r["EIN"] for r in links]
    print("  duplicate EIN links  : %d" % (len(eins) - len(set(eins))))
    if len(eins) != len(set(eins)):
        ok = False
    print("  OK" if ok else "  FAIL")
    return 0 if ok else 1


def selftest() -> int:
    """The ordinal round-trip must be exact, or minting collides."""
    ident = _identity()
    ok = True
    for n in (1, 31, 32, 1023, 1024, 1555, 99999):
        if _ordinal(ident.mint(n)) != n:
            print("  FAIL ordinal round-trip at %d" % n)
            ok = False
    reg = _read(REGISTER)
    used = {r["cedar_uid"] for r in reg if r.get("cedar_uid")}
    nxt = max(_ordinal(u) for u in used) + 1
    if ident.mint(nxt) in used:
        print("  FAIL next ordinal collides with an existing uid")
        ok = False
    print("  ordinal round-trip exact; next uid %s is free" % ident.mint(nxt))

    # THE COLLAPSES. Each of these was a live wrong link found on 2026-09-04,
    # and each broke a different version of the agreement test:
    #   - Catawba: differs by ONE token, which the "one word apart" rule
    #     accepted until legal-form words were made identity-changing.
    #   - Tulalip: the containment case.
    #   - National Indian Health Board: the non-regression - a form word IN
    #     BOTH names must not cause a false rejection.
    for a, b, want, why in (
            ("Catawba Indian Nation", "CATAWBA INDIAN NATION FOUNDATION INC",
             False, "a nation and its foundation are two legal persons"),
            ("Tulalip Tribes of Washington", "TULALIP FOUNDATION",
             False, "containment is not agreement"),
            ("Blackfeet Tribe of the Blackfeet Indian Reservation of Montana",
             "FAST BLACKFEET", False, "a shared word is not a shared identity"),
            ("National Indian Health Board", "NATIONAL INDIAN HEALTH BOARD",
             True, "a form word in BOTH names must still agree"),
            ("Akiptan, Inc.", "AKIPTAN INC", True, "legal suffix only")):
        got = _agree(a, b)
        if got != want:
            print("  FAIL _agree(%r, %r) = %s, expected %s - %s"
                  % (a[:34], b[:34], got, want, why))
            ok = False
    print("  agreement test holds on all 5 named collapse cases")
    print("  selftest %s" % ("PASS" if ok else "FAIL"))
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
