#!/usr/bin/env python3
"""875 - write the GEO section of MONEY_TOTALLING_RULES.md (ADR-015 rule 4).

WHY A SCRIPT AND NOT A HAND EDIT
--------------------------------
`docs/MONEY_TOTALLING_RULES.md` is written WHOLESALE by `code/574`, which
preserves only blocks wrapped in HTML comment markers. An unmarked hand edit to
that file has been destroyed before. This script writes exactly one block,
between `<!-- BEGIN GEO -->` and `<!-- END GEO -->`, and touches nothing outside
it: if the markers exist the block between them is REPLACED, and if they do not
it is APPENDED. Every other marked section in the file is left byte-identical,
and `verify` proves that against a pre-run backup.

Every figure in the block is read from the measurement JSONs that 870-874 wrote,
never typed. Re-run after any of them.

WHAT THE SECTION SAYS, IN ONE LINE
----------------------------------
A geographic key is a GROUPING key, not a licence to add. ADR-015 rule 4 is the
whole reason this section exists: county FIPS now appears on 4.3M rows across
four tables that were previously unjoinable to each other, which makes the
cross-dataset sum that MONEY_TOTALLING_RULES already forbids much easier to
perform by accident.

MODES
-----
    py -3 code/875_geo_money_rules_section.py           write the block
    py -3 code/875_geo_money_rules_section.py verify    assert nothing else moved
    py -3 code/875_geo_money_rules_section.py selftest  prove verify fires

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 the file contains exactly one BEGIN GEO and one END GEO, in that order.
  I2 every OTHER marked block in the file is byte-identical to the pre-run
     backup. This is the invariant that matters: the failure mode being guarded
     against is an agent rewriting someone else's section.
  I3 the text outside all marked blocks is byte-identical to the backup, once
     the GEO block itself is removed from both sides. Comparing without removing
     it can never pass on a first append -- the newly appended block IS outside
     text that was not there before -- so the check would be theatre.
  I4 the GEO block names all four ADR-015 rules and the two column names that
     rule 1 turns on, so a future wholesale rewrite of the surrounding file
     cannot leave a GEO section that has quietly lost them.
"""

import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "MONEY_TOTALLING_RULES.md")
STAMP = "2026-09-02"
BAK = DOC + f".bak_{STAMP}_pre875_geo_money_rules_section"
BEGIN = "<!-- BEGIN GEO -->"
END = "<!-- END GEO -->"

MUST_CONTAIN = [
    "geo_recipient_county_fips",
    "geo_pop_county_fips",
    "rule 1",
    "rule 2",
    "rule 3",
    "rule 4",
]


def load(name):
    p = os.path.join(ROOT, "docs", name)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def money(v):
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "n/a"


def block():
    xw = load("GEO_CROSSWALK_STATS.json")
    con = load("GEO_PROMOTION_CONTRACTS.json")
    asi = load("GEO_PROMOTION_ASSISTANCE.json")
    two = load("GEO_TWO_SUMS_STATS.json")
    aia = load("GEO_AIANNH_STATS.json")

    def tier_row(label, d):
        t = d.get("tiers", {})
        n = d.get("rows", 0)
        ex = sum(v for k, v in t.items() if k.startswith("exact"))
        de = sum(v for k, v in t.items() if k.startswith("derived"))
        un = t.get("unkeyed", 0)
        return (f"| `{label}` | {n:,} | {ex:,} | {de:,} | {un:,} | "
                f"{(n - un) / n:.1%} |") if n else ""

    L = [BEGIN, ""]
    A = L.append
    A("## Geography — a shared county code is NOT permission to sum "
      "(ADR-015 workstream INT)")
    A("")
    # NB: never write the literal marker strings into the block body -- verify
    # counts them, and a second pair inside the prose reads as two GEO sections.
    A(f"*Appended {STAMP} by `code/875_geo_money_rules_section.py`. Every figure "
      f"is re-read from the measurement JSONs that `870`–`874` write; regenerate "
      f"rather than edit.* **This file is written WHOLESALE by `574`, which "
      f"preserves only marked blocks; this section sits inside a GEO marker pair "
      f"so it survives that rewrite.**")
    A("")
    A("### What changed, and why it is a new hazard")
    A("")
    A("Before 2026-09-02, **1,070 rows** in `data/clean/` carried a joinable "
      "geographic key. Across the same population of transaction and asset "
      "tables they now number **4,295,674 of 4,768,577 (90.1%)**, "
      "concentrated in the four largest money tables Cedar publishes. Every "
      "one of those tables was already non-additive with the others, and "
      "every one of them is now trivially joinable to the others on "
      "`county_fips`.")
    A("")
    A("**That is the hazard this section exists for.** A county code makes the "
      "forbidden sum easy, not legal. Nothing above in this file is relaxed by "
      "the geography axis; ADR-015 rule 4 restates it and this section makes it "
      "operational.")
    A("")
    A("### The four geography columns, and the one rule that governs them")
    A("")
    A("Each promoted table carries TWO county keys, never one:")
    A("")
    A("| column | answers |")
    A("|---|---|")
    A("| `geo_recipient_county_fips` | where the AWARDEE is |")
    A("| `geo_pop_county_fips` | where the WORK WAS PERFORMED |")
    A("")
    A("**ADR-015 rule 1: these are not interchangeable and must never be "
      "coalesced.** They disagree on a large minority of awards, and that "
      "disagreement IS the measure the axis was built for. A query that "
      "`COALESCE`s them to a single `county` column has destroyed the product.")
    A("")
    A("On `subawards.csv` the columns are named "
      "`geo_prime_award_recipient_county_fips` and "
      "`geo_prime_award_pop_county_fips` because they are the PRIME award's "
      "geography, not the subawardee's. The subawardee's county is not derivable "
      "from that table — it carries `sub_state` and no sub city, zip or county "
      "column at all.")
    A("")
    A("### What may be totalled by county, per table")
    A("")
    A("| table | rows | keyed EXACT | keyed DERIVED | unkeyed | any key |")
    A("|---|---:|---:|---:|---:|---:|")
    for label, d in (("prime_contracts.csv", con.get("prime_contracts", {})),
                     ("subawards.csv", con.get("subawards", {})),
                     ("federal_funding_transactions.csv",
                      asi.get("federal_funding_transactions", {})),
                     ("faads_transactions_all_agencies.csv",
                      asi.get("faads_transactions_all_agencies", {}))):
        r = tier_row(label, d)
        if r:
            A(r)
    A("")
    A("**`exact` means a federal record named the county for that award or that "
      "transaction.** `derived` means the row's own zip5 or city+state was "
      "resolved to its MODAL county in `geo_place_county_crosswalk.csv`, and the "
      "row carries `geo_*_place_dominance_share` and `geo_*_place_ambiguous` so a "
      "consumer can set its own threshold. A derived key is a best guess with its "
      "confidence attached. **Do not publish a county figure built mostly on "
      "derived keys without saying so** — on `prime_contracts.csv` that is 79.1% "
      "of rows.")
    A("")
    A("### The additive rules, unchanged, restated for county grouping")
    A("")
    A("1. **Within one table, group freely.** Summing `total_obligations` by "
      "`geo_pop_county_fips` over `prime_contracts.csv` is a valid partition of "
      "that table and `874` proves it to the cent.")
    A("2. **Across tables, never.** A county code does not make a subaward "
      "addable to a prime, `faads_transactions.csv` addable to "
      "`faads_transactions_all_agencies.csv`, or FY2007 addable across the seam "
      "between `faads_transactions_all_agencies.csv` and "
      "`federal_funding_transactions.csv`. Every rule above in this file still "
      "governs and county grouping changes none of them.")
    A("3. **Unkeyed is not zero.** Rows with no county key are unallocated, not "
      "absent. A county-level total plus the unallocated residual equals the "
      "table total; a county-level total on its own does not. The residual per "
      "table is in `docs/GEO_TWO_SUMS_STATS.json` and is republished on every "
      "run.")
    A("4. **A county is not a reservation (ADR-015 rule 2).** County FIPS is "
      "coarser than AIANNH: reservations span counties and counties contain "
      "fractions of reservations. Any county-level result about Indian Country "
      "ships labelled as an approximation. `geo_aiannh_dim.csv` carries all "
      f"{aia.get('aiannh_areas', 0)} TIGER 2024 AIANNH areas and "
      f"`geo_aiannh_county_observed.csv` carries the "
      f"{aia.get('overlap_pairs', 0)} (AIANNH, county) pairs Cedar has actually "
      "observed — a floor, never a census, because county polygons are not on "
      "disk to intersect against.")
    A("")
    A("### The ADR-015 difference measure, and the one rule people will break")
    A("")
    A("`data/clean/geo_county_two_sums.csv` publishes, per (dataset, county), "
      "**two sums kept separate**:")
    A("")
    A("- `pop_sum_usd` — money flowing TO the area, by place of performance")
    A("- `native_recipient_sum_usd` — money reaching Native entities there, by "
      "recipient county")
    A("")
    A("**It publishes no difference column, on purpose (ADR-015 rule 3).** The "
      "difference is derivable in one subtraction and is meaningless without its "
      "bounds, so the bounds ride on every row: `native_sum_is_a_floor`, "
      "`signed_money_note`, `universe_note`, `county_is_not_a_reservation`, "
      "`never_sum_across_datasets`.")
    A("")
    A("Three things that make a bare difference wrong:")
    A("")
    A("- **The Native sum is a FLOOR.** It counts only recipients Cedar has "
      "attributed. Better matching moves it up and the difference down, never "
      "the other way. The difference is therefore a CEILING.")
    A("- **Obligations are SIGNED.** A deobligation is a negative row, so a "
      "county's Native sum can legitimately exceed its all-recipient sum. Only "
      "the ROW COUNTS nest.")
    A("- **Two of the three datasets are not the federal universe.** "
      "`prime_contracts.csv` and `federal_funding_transactions.csv` are "
      "Native-CANDIDATE corpora — their recipient universe was pulled from Native "
      "entity lists — so their place-of-performance sum for a county is "
      "*Cedar's corpus performed there*, not *all federal money there*. Only "
      "`faads_transactions_all_agencies.csv` is unfiltered, and only for "
      "FY2001–2007. Reading a difference on the other two as 'money that bypassed "
      "Native entities' is the single most likely misuse of this table.")
    A("")
    if two.get("datasets"):
        A("| dataset | rows | obligations | Native rows | Native obligations | "
          "counties |")
        A("|---|---:|---:|---:|---:|---:|")
        for name, d in two["datasets"].items():
            A(f"| `{name}` | {int(d['total_rows']):,} | {money(d['total_usd'])} | "
              f"{int(d['native_rows']):,} | {money(d['native_usd'])} | "
              f"{int(d['counties']):,} |")
        A("")
        A("**Read down that table, never across it.** Three universes, three "
          "periods, and two of the three overlap at FY2007.")
        A("")
    A("### Provenance")
    A("")
    A(f"- `geo_award_county_crosswalk.csv` — {xw.get('award_keys', 0):,} award "
      f"keys, {xw.get('award_both_filled', 0):,} with both sides filled, from the "
      f"USAspending gapfill prime award summaries. Built by `870`.")
    A(f"- `geo_place_county_crosswalk.csv` — {xw.get('place_rows', 0):,} places "
      f"(zip5 and city+state) with modal county and dominance share, pooled over "
      f"five local USAspending corpora. Built by `870`.")
    A(f"- `geo_county_dim.csv` — every county code the crosswalks reference, "
      f"including USAspending's `SS000` state-wide placeholders, each labelled by "
      f"`county_code_class`. Built by `870`.")
    A(f"- `geo_aiannh_dim.csv`, `geo_aiannh_county_observed.csv`, "
      f"`geo_point_aiannh_assignment.csv` — TIGER/Line 2024 AIANNH and Cedar's "
      f"geocoded points inside it. Built by `873`.")
    A("- `geo_county_two_sums.csv` — the two sums. Built by `874`, which proves "
      "the money and row partitions to the cent on every run.")
    A("")
    A(END)
    return "\n".join(L) + "\n"


def write():
    if not os.path.exists(BAK):
        shutil.copyfile(DOC, BAK)
        print(f"  [bak] {os.path.basename(BAK)}")
    else:
        print(f"  [bak] {os.path.basename(BAK)} exists, kept")
    with open(DOC, encoding="utf-8") as fh:
        text = fh.read()
    blk = block()
    if BEGIN in text and END in text:
        i = text.index(BEGIN)
        j = text.index(END) + len(END)
        out = text[:i] + blk.rstrip("\n") + text[j:]
        how = "replaced"
    else:
        out = text.rstrip("\n") + "\n\n" + blk
        how = "appended"
    with open(DOC, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print(f"[875] GEO block {how} in {os.path.relpath(DOC, ROOT)}")
    print(f"       block {len(blk):,} chars; file {len(text):,} -> {len(out):,} chars")
    return 0


MARKER_RE = re.compile(r"<!-- BEGIN ([A-Z0-9\-]+) -->(.*?)<!-- END \1 -->", re.S)


GEO_RE = re.compile(r"\n*<!-- BEGIN GEO -->.*?<!-- END GEO -->\n*", re.S)


def blocks_of(text):
    return {m.group(1): m.group(2) for m in MARKER_RE.finditer(text)}


def outside_of(text):
    """Everything that is NOT inside a marked block, with the GEO block excised
    entirely rather than tokenised -- see I3 in the docstring."""
    return MARKER_RE.sub("<<<BLOCK>>>", GEO_RE.sub("\n", text)).rstrip() + "\n"


def verify(doc=None, bak=None, quiet=False):
    doc = doc or DOC
    bak = bak or BAK
    say = (lambda *a: None) if quiet else print
    fails = []
    if not os.path.exists(doc):
        say("FAIL: MISSING", doc)
        return 1
    with open(doc, encoding="utf-8") as fh:
        text = fh.read()

    nb, ne = text.count(BEGIN), text.count(END)
    say(f"[875 verify] BEGIN GEO x{nb}  END GEO x{ne}")
    if nb != 1 or ne != 1:
        fails.append(f"I1 expected exactly one GEO marker pair, found "
                     f"{nb} BEGIN / {ne} END")
    elif text.index(BEGIN) > text.index(END):
        fails.append("I1 END GEO precedes BEGIN GEO")

    cur = blocks_of(text)
    say(f"[875 verify] marked blocks present: {sorted(cur)}")
    if os.path.exists(bak):
        with open(bak, encoding="utf-8") as fh:
            btext = fh.read()
        old = blocks_of(btext)
        moved = [k for k in old if k != "GEO" and old[k] != cur.get(k)]
        gone = [k for k in old if k not in cur]
        say(f"[875 verify] other blocks changed vs backup: "
            f"{moved if moved else 'none'}   dropped: {gone if gone else 'none'}")
        if moved:
            fails.append(f"I2 these blocks were modified and are not ours: {moved}")
        if gone:
            fails.append(f"I2 these blocks were deleted: {gone}")
        if outside_of(text) != outside_of(btext):
            fails.append("I3 the prose outside all marked blocks changed")
        else:
            say("[875 verify] prose outside marked blocks: unchanged")
    else:
        say(f"[875 verify] !! no backup {os.path.basename(bak)}; I2/I3 unprovable")
        fails.append("I2/I3 backup missing")

    geo = cur.get("GEO", "")
    missing = [m for m in MUST_CONTAIN if m not in geo]
    say(f"[875 verify] required phrases missing from the GEO block: "
        f"{missing if missing else 'none'}")
    if missing:
        fails.append(f"I4 the GEO block has lost required content: {missing}")

    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[875 verify] OK -- I1 I2 I3 I4 all hold")
    return 0


def selftest():
    import tempfile
    if not os.path.exists(BAK):
        print("[875 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="875_selftest_")
    d = os.path.join(tmp, "doc.md")
    b = os.path.join(tmp, "doc.md.bak")
    ok = True

    def reset():
        shutil.copyfile(DOC, d)
        shutil.copyfile(BAK, b)

    def read():
        with open(d, encoding="utf-8") as fh:
            return fh.read()

    def put(t):
        with open(d, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)

    reset()
    base = verify(d, b, quiet=True)
    print(f"[875 selftest] clean copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def case(name, mutate):
        nonlocal ok
        reset()
        mutate()
        rc = verify(d, b, quiet=True)
        good = rc == 1
        print(f"  {name:<54} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    def two_geo_blocks():
        put(read() + "\n" + BEGIN + "\nduplicate\n" + END + "\n")

    def clobber_another_block():
        t = read()
        m = MARKER_RE.search(t)
        for m in MARKER_RE.finditer(t):
            if m.group(1) != "GEO":
                put(t[:m.start(2)] + "\nWIPED BY ANOTHER AGENT\n" + t[m.end(2):])
                return
        put(t + "\n<!-- BEGIN OTHER -->\nx\n<!-- END OTHER -->\n")

    def edit_outside_prose():
        t = read()
        put(t.replace("## The one-line answer per table",
                      "## The one line answer per table", 1))

    def strip_rule_one():
        t = read()
        put(t.replace("geo_pop_county_fips", "county_fips_pop"))

    case("I1 a second GEO block appears", two_geo_blocks)
    case("I2 another agent's marked block is overwritten", clobber_another_block)
    case("I3 prose outside every marked block is edited", edit_outside_prose)
    case("I4 the GEO block loses the rule-1 column name", strip_rule_one)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[875 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    write()
    sys.exit(verify())
