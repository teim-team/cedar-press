#!/usr/bin/env python3
"""
Cedar Press - 500: the architecture map. GENERATED, READ-ONLY OUTPUT.

WHAT THIS IS FOR
----------------
"How many datasets do we have, what feeds each one, and what is missing?" was
a question nobody could answer from a document. On 2026-08-28 the product
catalog said 11 collections, `dist/` held 138 table directories, `data/clean`
held 278 tables, and a dataset that had been shipping for a week
(Native-Owned Businesses) was in none of the counts. Three separate stale
numbers were found the same day in the registry docs.

Every one of those is the same defect: a hand-maintained document describing a
moving system. So this file does not describe the architecture - it MEASURES
it, every run, and writes `docs/ARCHITECTURE.md`.

    py -3 code/500_build_architecture_map.py            # write docs/ARCHITECTURE.md
    py -3 code/500_build_architecture_map.py --check    # exit 1 if the map is stale

THE ONE THING YOU EDIT
----------------------
`COLLECTIONS` below. It is the only declared knowledge in this file: which
`dist/` number-prefixes and which clean tables belong to which product
collection. Everything else is measured from disk.

When a new dataset lands, add one entry here. The ORPHANS section of the output
exists so that forgetting is loud: any `dist/` directory or `data/clean` table
that no collection claims is listed, by name, every run.

NOT A GATE
----------
This reports; it does not fail a build. `62_no_regression_check.py` is the gate.
Keeping them separate is deliberate - a reporting tool that can block work gets
routed around, and this one is meant to be read.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CLEAN = ROOT / "data" / "clean"
CODE = ROOT / "code"
DOCS = ROOT / "docs"
OUT = DOCS / "ARCHITECTURE.md"

SCRIPT = "500_build_architecture_map.py"

# ---------------------------------------------------------------------------
# THE DECLARED MAP - the only hand-maintained knowledge in this file.
#
# `shelf` mirrors src/features/grove/pressCatalog.js in the product repo. If the
# two disagree, the catalog is authoritative for pricing and this is wrong.
# `prefixes` are dist/ number-prefix families. `extra_tables` names clean tables
# that belong to a collection but do not live under its prefix.
# ---------------------------------------------------------------------------
# `tables` is a REGEX matched against every `data/clean/*.csv` stem. Listing
# headline tables by hand under-reported badly: the first version claimed 1-3
# tables per collection while 157 tables carry an entity id, so Native Hawaiian
# Organizations read as 4-of-210 covered when `nho_*` tables were simply never
# read. A pattern claims the whole family, and anything no pattern claims is
# reported under "Unattributed" rather than disappearing.
COLLECTIONS: list[dict] = [
    # --- Cedar Press (standard) -------------------------------------------
    {"id": "funding", "name": "Federal Funding to Indian Country", "shelf": "standard",
     "prefixes": ["03"],
     # `usac_` added 2026-09-02 (workstream ACQUIRE-1119-1121, code/1120).
     # Universal Service Fund money - E-Rate commitments to tribal schools and
     # libraries, and Rural Health Care commitments - is federal funding to
     # Indian Country that arrives through the FCC's universal service
     # mechanism rather than through USAspending, so no existing pattern
     # reaches it. The E-Rate slice is the collection's first TYPE_FILTER-only
     # leg from a publisher that did the Native identification itself.
     "tables": r"^(federal_funding|faads_|assistance_|bie_uio|native_passthrough|funding_identifier|inflation_deflator|usac_)"},
    {"id": "federal-register", "name": "Federal Register", "shelf": "standard",
     "prefixes": ["09"],
     # `dear_tribal_leader` and `dtll_` added 2026-09-02 (workstream FR-DTLL).
     # The letters are the non-Federal-Register half of the same consultation
     # record this collection already ships: `consultation_events.csv` typed
     # six rows `dear_tribal_leader_letter` because the FR is the only place
     # it looks. Without this pattern both tables reach no collection and 512
     # counts them as shippable-with-no-owner.
     "tables": r"^(federal_actions|fr_(?!nagpra)|section_106|consultation_|correspondence_foia|nepa_|dear_tribal_leader|dtll_)"},
    {"id": "legislation", "name": "Congressional Votes and Proposed Legislation", "shelf": "standard",
     "prefixes": ["10"],
     "tables": r"^(bill_|native_bill|congress|member_positions|native_issue_litigation)"},
    {"id": "deals", "name": "Indian Country Deals", "shelf": "standard",
     "prefixes": ["01"],
     "tables": r"^(deals_|tribal_resolution_financings|seminole_bond|ownership_events)"},
    {"id": "nagpra", "name": "NAGPRA", "shelf": "standard",
     "prefixes": ["11"],
     "tables": r"^(nagpra_|fr_nagpra)"},
    {"id": "lobbying", "name": "Lobbying", "shelf": "standard",
     "prefixes": ["04", "18"],
     # `nonprofit_schedule_c` added 2026-09-02 (workstream INT-READY). Both
     # tables were ORPHANS - built, in dist/ with notes under the 04w_ prefix
     # (the lobbying family), and claimed by no collection, so 512 counted
     # them as shippable-with-no-owner and they reached no contract. This
     # collection's own descriptor already promises them: "...hearing
     # testimony and nonprofit Schedule C." The pattern is spelled out rather
     # than folded into `^np_` because these are LOBBYING records that happen
     # to come out of a 990 - the nonprofits collection owns the filer, this
     # one owns what the filer reported spending on lobbying.
     "tables": r"^(lobbying_|native_entity_lobbying|advocacy_|ferc_|admin_appeal|nrc_|oira_|hearing_|earmark|fr_ex_parte|agency_attention|tribe_year_lobbying|nonprofit_schedule_c)"},

    # --- Cedar Press+ (pro) ------------------------------------------------
    {"id": "contractors", "name": "Federal Prime Contracting", "shelf": "pro",
     "prefixes": ["02"],
     "tables": r"^(prime_contracts|fpds_|sam_prime|contractor_)",
     "exclude_dirs": ["02b_subcontracting", "02f_individual_native_verification",
                      "02i_individual_native_firm_register",
                      "02j_individual_native_firm_contracts",
                      "02k_individual_native_firm_contracts_published",
                      "02l_individual_native_exclusion_pairs"]},
    {"id": "subcontracting", "name": "Federal Subcontracting", "shelf": "pro",
     "prefixes": [], "dirs": ["02b_subcontracting", "02p_subaward_entity_rollup"],
     "tables": r"^(subaward|subcontract|prime_sub_network)"},
    {"id": "native-owned-businesses", "name": "Native-Owned Businesses", "shelf": "pro",
     "prefixes": [],
     "dirs": ["02f_individual_native_verification", "02i_individual_native_firm_register",
              "02j_individual_native_firm_contracts",
              "02k_individual_native_firm_contracts_published",
              "02l_individual_native_exclusion_pairs"],
     # NOTE 2026-08-28: the newest facts for this collection -
     # `tribal_certification_facts_2026-08-28.csv` (26 rows, 22 carrying
     # THIRD_PARTY_TRIBAL_GOVT from White Earth) - are in
     # `data/staging/tribal_vendor_lists/`, NOT in `data/clean`. That is why
     # this collection shipped without ever entering the registries. Promote
     # them to data/clean and the pattern below will pick them up.
     #
     # These firms are owned by PEOPLE, not nations. `individual_native_*`
     # tables key on `surrogate_entity_id` and one carries
     # `refuses_tribal_link_not_native_ownership` - an absent tribal id here is
     # correct by design, not a gap. They join the spine on its 45
     # "Individually Native-owned business" rows.
     "tables": r"^(individual_native|tribal_certification)"},
    # Added 2026-09-02 by code/1072_tribally_owned_enterprises.py. The 14th
    # collection, and it is a DIFFERENT RELATION from
    # `native-owned-businesses`, not a bigger version of it:
    #   native-owned-businesses   a nation CERTIFIED or LISTED this firm
    #                             -> affiliated_with
    #   nest                      a nation, ANC or NHO OWNS this enterprise,
    #                             or published a non-ownership tie to it
    #                             -> owned_by / affiliated_with, declared per
    #                                row in `relation_class`
    # The two must not be merged. The `identity_scope` gradient in
    # native_owned_businesses runs down to `vendor_relationship`, which is no
    # ownership claim at all, and flattening it is what
    # docs/PUBLICATION_POLICY.md refuses.
    {"id": "nest", "name": "NEST: Native Enterprise Structures and Ties",
     "shelf": "pro", "prefixes": [],
     "tables": r"^nest_"},
    # Added 2026-09-02 by code/1105_newsletter_corpus_ship.py. The 15th
    # collection. It is a FINDING AID, not a text corpus: one row per
    # publication channel a Native entity operates, with the archive depth its
    # own index exposes, plus a coverage ledger whose denominator is the whole
    # spine. Nobody publishes a cross-nation catalogue of tribal periodicals -
    # the closest published things are single-nation mastheads and the Native
    # American Journalists Association's membership list, neither of which is
    # a denominator.
    #
    # WHAT IT DELIBERATELY IS NOT: the issues. Depth is measured from the
    # index and the media library; back issues are not downloaded in bulk, and
    # no issue body text enters Cedar, because a tribal newspaper carries
    # obituaries, health notices and family announcements about people who are
    # not public figures. 990's invariant 7 fails the build on any field over
    # 1,200 characters, which is the shape body text would arrive in.
    #
    # `shelf` is `standard`: this is a catalogue of what Indian Country
    # publishes, and the product catalog (src/features/grove/pressCatalog.js)
    # needs a matching entry before it is priced.
    {"id": "newsletters", "name": "The Native Press: Tribal Newsletters and "
     "Periodicals", "shelf": "standard", "prefixes": [],
     "tables": r"^tribal_newsletter_"},
    {"id": "natural-resources", "name": "Natural Resource Revenues", "shelf": "pro",
     "prefixes": ["12", "15"],
     # NOTE 2026-09-02 (workstream ACQUIRE-1119-1121): no pattern change was
     # needed for the BIA mineral acreage table - it is deliberately named
     # `resource_bia_mineral_acreage_tracts.csv` so `^resource_` claims it and
     # the `^bia_` pattern in `_entity_layer` below does NOT, which keeps the
     # 249,165-row acreage denominator out of the entity layer by construction
     # rather than by regex ordering. It answers WHAT_IS_MISSING
     # natural-resources #3: "revenue with no denominator".
     "tables": r"^(resource_|tribal_tax|nd_severance|tribal_debt|tribal_bond|anc_ceiling|ancsa_)"},
    {"id": "nonprofits", "name": "Native Nonprofits", "shelf": "pro",
     "prefixes": ["06", "17"],
     "tables": r"^(np_|grantmaker_|grantee_|fac_tribal)"},

    # --- Cedar Grove -------------------------------------------------------
    {"id": "gaming", "name": "Gaming Intelligence", "shelf": "grove",
     "prefixes": ["07", "14", "16"],
     "tables": r"^(gaming_|sec_gaming_|nigc_|compact_|casino|loyalty_|digital_gaming|wa_machine|compacts|ca_gaming|fl_gaming|state_gaming|fac_audit_)"},

    # --- Infrastructure: not sold as a collection, but everything joins it --
    {"id": "_entity_layer", "name": "Entity spine, identifiers and reference", "shelf": "infrastructure",
     "prefixes": ["00", "05", "08", "13"],
     # `bia_` and `nppes_` added 2026-09-02 (workstream ACQUIRE-1119-1121).
     #   bia_*    the BIA's own ArcGIS server, biamaps.geoplatform.gov: the
     #            tribal leaders directory as structured fields rather than
     #            the HTML `bia_directory` source reads today, the 335 Land
     #            Area Records, the 93-office facility register, the 84 dated
     #            PL 102-477 plan agreements, and `bia_ofa_petitioners.csv` -
     #            20 Office of Federal Acknowledgment petitioners, which is
     #            the NEGATIVE CASE docs/ASSERTION_LAYER.md records as absent
     #            ("entity.is_federally_recognized has no negative case").
     #   nppes_   CMS enumeration. A THIRD evidence family for entity.state /
     #            entity.city / legal name, independent of both the FR roster
     #            and the IRS BMF. It is infrastructure, not a product: it
     #            exists to be arbitrated by code/1118_corroboration_layer.py.
          # `cedar_place` added 2026-09-02 (workstream PLACE-IDS, ADR-030,
     #   code/1129). `cedar_places.csv` is the directory of PHYSICAL
     #   PLACES a Cedar entity operates - gaming property, BIE school,
     #   IHS facility, BIA office - each carrying a permanent
     #   `CEDAR-PLACE-nnnnnn-CC`. A place is a SUB-HUB of the entity
     #   that operates it (IDENTIFIER_STANDARD SS2), never a peer, so it
     #   is infrastructure in this collection rather than a row in the
     #   gaming product - the same call `bie_`/`bia_` already got.
"tables": (r"^(cedar_entity|cedar_place|cedar_identifier|cedar_publishable|cedar_ruling|cedar_correction|cross_dataset_ruling|entity_|identifier_|alias|"
                r"nho_|tcu_|uio_|bie_|bia_|nppes_|native_fi|federal_recognition|intertribal|"
                r"admin_region|foia_|visitor_|state_recognized)")},
]

# Tables whose name matches one of these is plumbing, not a dataset.
ORPHAN_IGNORE = re.compile(r"^(codebook_|coverage_audit|_|tmp_|scratch_)", re.I)


def read_rows(path: Path) -> int | None:
    """Row count excluding the header. None if unreadable."""
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            n = sum(1 for _ in f)
        return max(0, n - 1)
    except OSError:
        return None


def dist_dirs() -> list[str]:
    return sorted(p.name for p in DIST.iterdir() if p.is_dir()) if DIST.exists() else []


def clean_tables() -> dict[str, Path]:
    if not CLEAN.exists():
        return {}
    return {p.stem: p for p in sorted(CLEAN.glob("*.csv"))}


def script_writers() -> dict[str, list[str]]:
    """table stem -> scripts that appear to WRITE it.

    Heuristic and labelled as such in the output: a script counts as a writer if
    it names `<table>.csv` and also calls a write. It cannot distinguish a
    full-rebuild writer from an in-place enricher - that is class6, and
    `293_lint_bug_classes.py` is the detector for it.
    """
    writes: dict[str, list[str]] = defaultdict(list)
    tables = set(clean_tables())
    for p in sorted(CODE.glob("*.py")):
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not re.search(r"to_csv\(|csv\.writer|\.write_text\(|open\([^)]*['\"]w", src):
            continue
        for t in tables:
            if re.search(rf"\b{re.escape(t)}\.csv", src):
                writes[t].append(p.name)
    return writes


def notes_contract(dirname: str) -> tuple[int, int]:
    """(tables declared in this dist dir, how many carry a human NOTES.md).

    `dist/` is the CONTRACTS layer, not the data: measured 2026-08-28 it holds
    292 `.notes.json`, 212 `.NOTES.md` and exactly ONE `.csv`. So a "table" here
    is a declared `<name>.notes.json`, and the second number is how many of
    those also have the human-readable `<name>.NOTES.md` beside them. Counting
    `*.csv` would report zero for every collection and look like a build
    failure rather than the shape of the directory.
    """
    d = DIST / dirname
    if not d.is_dir():
        return (0, 0)
    declared = {p.name[: -len(".notes.json")] for p in d.glob("*.notes.json")}
    human = {p.name[: -len(".NOTES.md")] for p in d.glob("*.NOTES.md")}
    return (len(declared), len(declared & human))


def resolve_tables(spec: dict, tables: dict[str, Path]) -> list[str]:
    """Clean tables claimed by this collection's `tables` regex.

    Backups and part-files are excluded: `.bak_*` sits beside a live table and
    would double every count while looking like real coverage.
    """
    pat = spec.get("tables")
    if not pat:
        return []
    rx = re.compile(pat)
    return sorted(t for t in tables if rx.search(t) and ".bak_" not in t
                  and not t.endswith(".part"))


def resolve_dirs(spec: dict, all_dirs: list[str]) -> list[str]:
    if spec.get("dirs"):
        return [d for d in spec["dirs"] if d in all_dirs]
    out = []
    excl = set(spec.get("exclude_dirs", []))
    for pref in spec.get("prefixes", []):
        for d in all_dirs:
            if d in excl:
                continue
            m = re.match(r"^(\d+)", d)
            if m and m.group(1) == pref:
                out.append(d)
    return sorted(set(out))


def build() -> str:
    all_dirs = dist_dirs()
    tables = clean_tables()
    writers = script_writers()

    claimed_dirs: set[str] = set()
    claimed_tables: set[str] = set()
    sections: list[str] = []

    by_shelf: dict[str, list[dict]] = defaultdict(list)
    for spec in COLLECTIONS:
        by_shelf[spec["shelf"]].append(spec)

    # ---- summary table ----
    lines: list[str] = []
    lines.append("# Cedar Press — architecture map")
    lines.append("")
    lines.append(f"*GENERATED by `code/{SCRIPT}` on "
                 f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
                 f"**Do not hand-edit** — fix the script, or the `COLLECTIONS` map inside it.*")
    lines.append("")
    lines.append("Every number here is measured from disk on the run that wrote this file. "
                 "The one piece of declared knowledge is which `dist/` prefixes and clean "
                 "tables belong to which collection; that lives in `COLLECTIONS` in the "
                 "script. Anything no collection claims is listed under **Orphans**, so "
                 "forgetting a dataset is loud rather than silent.")
    lines.append("")

    rows = []
    for spec in COLLECTIONS:
        dirs = resolve_dirs(spec, all_dirs)
        claimed_dirs |= set(dirs)
        tabs = resolve_tables(spec, tables)
        claimed_tables |= set(tabs)
        n_rows = sum(read_rows(tables[t]) or 0 for t in tabs)
        tot_tables = sum(notes_contract(d)[0] for d in dirs)
        tot_notes = sum(notes_contract(d)[1] for d in dirs)
        rows.append((spec, dirs, tabs, n_rows, tot_tables, tot_notes))

    lines.append("| collection | shelf | dist dirs | dist tables | with NOTES | headline rows |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for spec, dirs, tabs, n_rows, tot_tables, tot_notes in rows:
        gap = "" if tot_tables == tot_notes else f" ⚠"
        lines.append(f"| **{spec['name']}** (`{spec['id']}`) | {spec['shelf']} | "
                     f"{len(dirs)} | {tot_tables} | {tot_notes}{gap} | "
                     f"{n_rows:,} |")
    lines.append("")

    shipped = [s for s in COLLECTIONS if s["shelf"] != "infrastructure"]
    lines.append(f"**{len(shipped)} product collections** "
                 f"({sum(1 for s in shipped if s['shelf']=='standard')} standard · "
                 f"{sum(1 for s in shipped if s['shelf']=='pro')} pro · "
                 f"{sum(1 for s in shipped if s['shelf']=='grove')} grove), "
                 f"plus the shared entity layer.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- per collection ----
    for spec, dirs, tabs, n_rows, tot_tables, tot_notes in rows:
        lines.append(f"## {spec['name']}  ·  `{spec['id']}`  ·  {spec['shelf']}")
        lines.append("")
        if tabs:
            lines.append("**Headline tables**")
            lines.append("")
            lines.append("| table | rows | built by |")
            lines.append("|---|---:|---|")
            for t in tabs:
                w = writers.get(t, [])
                wtxt = ", ".join(f"`{x}`" for x in w[:4]) + (" …" if len(w) > 4 else "")
                lines.append(f"| `{t}.csv` | {read_rows(tables[t]) or 0:,} | {wtxt or '—'} |")
            lines.append("")
        if dirs:
            lines.append(f"**Ships to {len(dirs)} `dist/` "
                         f"{'directory' if len(dirs)==1 else 'directories'}**")
            lines.append("")
            for d in dirs:
                n, have = notes_contract(d)
                flag = "" if n == have else f"  ⚠ {n-have} of {n} missing a NOTES contract"
                lines.append(f"- `dist/{d}/` — {n} table{'' if n==1 else 's'}{flag}")
            lines.append("")
        else:
            lines.append("*No `dist/` directory claimed — this collection does not ship yet.*")
            lines.append("")
        lines.append("---")
        lines.append("")

    # ---- orphans ----
    lines.append("## Orphans — claimed by no collection")
    lines.append("")
    lines.append("Add these to `COLLECTIONS` in the script, or accept them as plumbing. "
                 "This section is the reason a forgotten dataset cannot stay invisible.")
    lines.append("")

    orphan_dirs = [d for d in all_dirs if d not in claimed_dirs]
    lines.append(f"**`dist/` directories: {len(orphan_dirs)} of {len(all_dirs)}**")
    lines.append("")
    if orphan_dirs:
        for d in orphan_dirs:
            lines.append(f"- `dist/{d}/`")
    else:
        lines.append("*none*")
    lines.append("")

    orphan_tables = [t for t in sorted(tables)
                     if t not in claimed_tables and not ORPHAN_IGNORE.match(t)]
    lines.append(f"**`data/clean` tables not named by any collection: "
                 f"{len(orphan_tables)} of {len(tables)}**")
    lines.append("")
    lines.append("*Most of these are legitimately intermediate. The ones worth claiming are "
                 "the ones a reader would expect to find in a collection.*")
    lines.append("")
    for t in orphan_tables[:60]:
        n = read_rows(tables[t])
        lines.append(f"- `{t}.csv` — {n:,} rows" if n is not None else f"- `{t}.csv`")
    if len(orphan_tables) > 60:
        lines.append(f"- …and {len(orphan_tables)-60} more")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## How to add a dataset")
    lines.append("")
    lines.append("1. Add an entry to `COLLECTIONS` in "
                 f"`code/{SCRIPT}` — id, name, shelf, and its `dist/` prefixes or `dirs`.")
    lines.append("2. Add the matching entry to `src/features/grove/pressCatalog.js` in the "
                 "**product repo**, on the same shelf. The catalog is authoritative for pricing.")
    lines.append("3. Give every shipped table a codebook block and a `.NOTES.md` contract, "
                 "then re-run the full ship chain per `docs/SHIPPING_RUNBOOK.md` "
                 "(`py -3 code/build.py ship`) — seven steps, not the "
                 "`87 → 25 → 27` shorthand, which omits the codebook build, the "
                 "gate, the coverage profile and the harmonised views.")
    lines.append("4. Re-run this script. The collection should leave **Orphans** and appear above.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if docs/ARCHITECTURE.md is missing or out of date")
    args = ap.parse_args()

    body = build()
    # The timestamp line changes every run; compare everything else.
    def strip_stamp(s: str) -> str:
        return "\n".join(l for l in s.splitlines() if not l.startswith("*GENERATED by"))

    if args.check:
        if not OUT.exists():
            print(f"MISSING: {OUT.relative_to(ROOT)} — run this script", file=sys.stderr)
            return 1
        if strip_stamp(OUT.read_text(encoding="utf-8")) != strip_stamp(body):
            print(f"STALE: {OUT.relative_to(ROOT)} does not match the tree — re-run this script",
                  file=sys.stderr)
            return 1
        print("architecture map current", file=sys.stderr)
        return 0

    tmp = OUT.with_suffix(".md.part")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
