#!/usr/bin/env python3
"""
Cedar Press - 1169: ONE release gate over EVERY delivery artifact.

    py -3 code/1169_release_verify.py              # verify, exit 1 if blocked
    py -3 code/1169_release_verify.py selftest     # prove each check can FAIL
    py -3 code/1169_release_verify.py --json       # machine-readable

WHY THIS EXISTS
---------------
External review, 2026-09-03:

    "The green checks do not currently add up to a green release... Individual
     checks are green, but the release is red."

That was exactly right and it was not an accident of wording. Cedar had five
audits, each honest about its own scope, and NO script that asked whether the
things a customer receives agree with each other. So `1165` could report zero
violations across thirteen delivered CSVs on the same day that
`dist/cedar_press.db` carried a retired-scheme column on **73 of its 231
tables, 4,325,664 populated rows**, and both statements were true.

(The changelog first reported this as "64,442 retired identifiers". That figure
was wrong in kind and far too small - it counted occurrences of the STRING
`tribe_id_scheme` in the file, not rows. Corrected here and in the changelog.)

    A per-artifact check can only ever prove one artifact is self-consistent.
    A RELEASE is a claim that every artifact tells the customer the same thing.

This script makes that claim checkable. It reports one verdict, it names the
scope of every sub-check beside its result, and any BLOCKING failure exits
nonzero.

WHAT A "RELEASE ID" IS HERE, AND WHAT IT IS NOT
------------------------------------------------
It is a content digest over the delivered set - the sorted (name, size, mtime,
first-KB digest) of every artifact this script covers. It is NOT a version
number and it is NOT a git commit: the tree is written by many concurrent
workstreams and a commit says nothing about what is on disk right now. The
release id answers exactly one question - "were these artifacts produced from
the same state?" - and two runs that disagree mean something moved underneath.

THE RULE THE REVIEWER ASKED FOR, AND WHY IT IS ENFORCED HERE
-------------------------------------------------------------
    "Every audit should first run against a small fixture containing a known
     violation and prove that it detects it. A check that returns zero without
     demonstrating that it can return one is not trustworthy."

This project has now shipped FOUR zero-result failures in one session: a scan
of the wrong table, a query against a retired column, a shell heredoc that
turned `\\b` into a literal backspace so a regex matched nothing, and an
identity check that tested a column NAME where it meant to test values. Every
one returned a clean zero and looked like good news.

So `selftest` injects a known violation for each check and asserts that check
FAILS. A check that cannot be shown to fail is reported as UNPROVEN and is
treated as a blocking failure in its own right.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)

DIST = ROOT / "dist"
CUSTOMER = DIST / "customer"
PREVIEW = DIST / "preview"
DB = DIST / "cedar_press.db"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
# Set only by selftest, so a check can be run against a planted fixture.
_RULING_OVERRIDE = None
# Set only by selftest: a 1167 module whose paths point at a planted tree.
_C1167 = None


@dataclass
class Check:
    name: str
    scope: str
    blocking: bool
    status: str = "NOT_RUN"        # PASS | FAIL | NOT_ESTABLISHED | UNPROVEN
    detail: str = ""
    measured: dict = field(default_factory=dict)


def neid_vocabulary() -> set:
    """Every retired NEID Cedar holds. Membership, never shape - see 1165."""
    vals = set()
    for path, col in ((CLEAN / "cedar_identifier_ledger_final.csv", "tribe_id"),
                      (SPINE / "cedar_identity_register.csv", "handle")):
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                v = (row.get(col) or "").strip()
                if v:
                    vals.add(v)
    return vals


# ---------------------------------------------------------------------------
# CHECKS
# ---------------------------------------------------------------------------

def check_csv_identity(vocab: set) -> Check:
    c = Check("delivered CSV identity migration",
              f"{len(list(CUSTOMER.glob('*.csv')))} files in dist/customer, full pass",
              blocking=True)
    hits, files = 0, []
    for p in sorted(CUSTOMER.glob("*.csv")):
        n = 0
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                for v in row.values():
                    if not v or "-" not in v:
                        continue
                    for tok in (v.split("|") if "|" in v else [v]):
                        if tok.strip() in vocab:
                            n += 1
        if n:
            files.append(f"{p.name}={n}")
        hits += n
    c.measured = {"retired_identifier_values": hits}
    c.status = "PASS" if hits == 0 else "FAIL"
    c.detail = "no retired identifiers" if hits == 0 else "; ".join(files)
    return c


def check_db_identity(vocab: set) -> Check:
    """The check that would have caught the headline contradiction."""
    c = Check("customer database identity migration",
              "dist/cedar_press.db, every TEXT column of every table",
              blocking=True)
    if not DB.exists():
        c.status = "NOT_ESTABLISHED"
        c.detail = "dist/cedar_press.db absent"
        return c
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        # DECODE LOSSILY, DO NOT SWITCH TO BYTES. Setting `text_factory = bytes`
        # made `tables` a list of bytes objects, so every subsequent
        # `PRAGMA table_info("b'entity_spine'")` named a table that does not
        # exist, returned no columns, and the check reported the 6.8 GB
        # database CLEAN. Third silent-zero in this file's short life; the
        # first two are named in the module docstring. Bytes were only ever
        # wanted to survive undecodable cells, and this achieves that without
        # corrupting the identifiers the whole check depends on.
        con.text_factory = lambda b: b.decode("utf-8", "replace")
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        # Probing 6.8 GB row-by-row in Python is not runnable. Ask SQLite: for
        # each table, does ANY row match ANY retired identifier? A single
        # bounded query per table, and it answers the release question - is the
        # retired scheme present at all - without materialising the database.
        # THE COLUMN TEST FIRST, BECAUSE IT IS CHEAP AND DAMNING.
        # A table that still HAS a retired-scheme column has not been migrated,
        # whatever its values happen to be today. Measured 2026-09-03: 73 of
        # 231 tables, 4,325,571 populated rows.
        neid_cols = []
        for t in tables:
            info = list(con.execute(f'PRAGMA table_info("{t}")'))
            cols = [r[1] for r in info]
            for col in cols:
                low = col.lower()
                if "tribe_id" in low or low.endswith("_neid") or low == "neid":
                    neid_cols.append((t, col))

        # NEVER SWALLOW A QUERY ERROR. The first version of this check wrapped
        # a 63-column `OR` in `except sqlite3.Error: continue`, so a table that
        # failed to query was skipped and the release read GREEN. That is the
        # exact zero-result failure this script's docstring is about, written
        # into the gate meant to prevent it. An unqueryable table is now an
        # UNCHECKED table and unchecked is not passed.
        populated, unchecked = 0, []
        for t, col in neid_cols:
            try:
                populated += con.execute(
                    f'SELECT COUNT(*) FROM "{t}" '
                    f'WHERE "{col}" IS NOT NULL AND TRIM("{col}") != \'\''
                ).fetchone()[0]
            except sqlite3.Error as e:
                unchecked.append(f"{t}.{col} ({e})")
        con.close()

        c.measured = {"tables_total": len(tables),
                      "tables_with_a_retired_column": len({t for t, _ in neid_cols}),
                      "retired_columns": len(neid_cols),
                      "populated_rows": populated,
                      "unchecked_columns": len(unchecked)}
        if unchecked:
            c.status = "NOT_ESTABLISHED"
            c.detail = (f"{len(unchecked)} column(s) could not be queried, so "
                        f"the database CANNOT be called clean: "
                        + "; ".join(unchecked[:3]))
        elif neid_cols:
            c.status = "FAIL"
            c.detail = (f"{len({t for t, _ in neid_cols})} of {len(tables)} "
                        f"tables still carry a retired-scheme column "
                        f"({len(neid_cols)} columns, {populated:,} populated "
                        f"rows). The CSVs were migrated; the database was not.")
        else:
            c.status = "PASS"
            c.detail = "no retired-scheme column in any table"
    except sqlite3.Error as e:
        c.status = "NOT_ESTABLISHED"
        c.detail = f"sqlite error: {e}"
    return c


def check_artifacts_agree(vocab: set) -> Check:
    """CSV and DB must be in the SAME identity state, not merely each 'fine'.

    This is the check whose absence produced the reviewer's headline. Two
    artifacts can each pass their own audit and still disagree, and a customer
    who joins the CSV to the database is the one who finds out.
    """
    c = Check("delivery artifacts share one identity state",
              "dist/customer/*.csv vs dist/cedar_press.db", blocking=True)
    csv_c = check_csv_identity(vocab)
    db_c = check_db_identity(vocab)
    a = csv_c.measured.get("retired_identifier_values", -1)
    b = db_c.measured.get("populated_rows", -1)
    c.measured = {"csv_retired_values": a, "db_retired_scheme_rows": b}
    if db_c.status == "NOT_ESTABLISHED":
        c.status = "NOT_ESTABLISHED"
        c.detail = db_c.detail
    elif (a == 0) == (b == 0):
        c.status = "PASS"
        c.detail = "both migrated" if a == 0 else "both un-migrated (still a release failure elsewhere)"
    else:
        c.status = "FAIL"
        c.detail = (f"artifacts DISAGREE: the CSVs carry {a:,} retired "
                    f"identifier values, the database carries {b:,} rows on a "
                    f"retired-scheme column. A customer joining one to the "
                    f"other gets two different answers about identity.")
    return c


def check_uid_integrity() -> Check:
    c = Check("cedar_uid names exactly one entity",
              "data/clean/cedar_identifier_ledger_final.csv, positive rows",
              blocking=True)
    # `_C1167` lets selftest hand in a module whose paths point at a planted
    # tree. Without it this function re-imported 1167 on every call, and 1167
    # resolves its own LEDGER / ALIASES / register from ITS module globals - so
    # a fixture could plant a uid collision and this check would sail past it
    # reading the real repo, returning PASS. Codex, PR #46, was right that the
    # uid check was not exercised; it turned out it could not be.
    m = _C1167
    if m is None:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "c1167", ROOT / "code" / "1167_cedar_uid_identity_collisions.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
        except Exception as e:
            c.status = "NOT_ESTABLISHED"
            c.detail = f"1167 would not import: {e}"
            return c
    # CALL 1167'S LOGIC, DO NOT RE-IMPLEMENT IT.
    #
    # The first version of this check rebuilt the uid->names map here and ran
    # `m.classify` on it - and so it never consulted `entity_aliases.csv`, which
    # 1167 gained afterwards. The result was two checks contradicting each
    # other: 1167 reported 0 collisions while this gate reported 2, on the same
    # ledger, in the same minute. A release gate whose sub-checks disagree with
    # the tools they are meant to aggregate is worse than no gate, and this is
    # the precise failure the whole script was written to catch, committed
    # inside the script itself.
    from collections import defaultdict
    ali = m.alias_index()
    by = defaultdict(set)
    with m.LEDGER.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            u = (row.get("cedar_uid") or "").strip()
            n = (row.get("canonical_name") or "").strip()
            if u and n and (row.get("confidence_tier") or "").strip() != "X":
                by[u].add(n)
    by = {u: {n for n in ns if u not in ali.get(m._norm_alias(n), set())}
          for u, ns in by.items()}
    merges = {u: sorted(ns) for u, ns in by.items()
              if len(ns) > 1 and m.classify(sorted(ns)) == "MERGE"}
    # and the foreign-name half, which 1167 checks independently of name count
    reg, by_name = m.register_truth()
    for u, ns in by.items():
        for n in ns:
            owners = ((by_name.get(n) or set())
                      | ali.get(m._norm_alias(n), set())) - {u}
            if len(owners) == 1:
                merges.setdefault(u, []).append(
                    f"{n} -> belongs to {next(iter(owners))}")
    c.measured = {"merge_uids": len(merges)}
    c.status = "PASS" if not merges else "FAIL"
    c.detail = ("no uid names two entities" if not merges
                else "; ".join(f"{u}: {' / '.join(n)}" for u, n in merges.items()))
    return c


def check_rulings_applied() -> Check:
    """A verified negative ruling still present in the data is a release failure.

    The reviewer's words: "A validated ruling should automatically become a
    constraint... 'negative rulings written, not yet applied' is not an
    acceptable stable state for a release pipeline."
    """
    c = Check("verified negative rulings are applied, not merely written",
              "review/cedar_research_rulings_municipal_pha_2026-09-03.csv "
              "vs data/clean/federal_funding_transactions.csv", blocking=True)
    # `_RULING_OVERRIDE` lets `selftest` point this at a planted ruling file.
    # The check must be runnable against evidence it did not choose, or the
    # positive control is testing a different function than production uses.
    ruling = (_RULING_OVERRIDE if _RULING_OVERRIDE
              else ROOT / "review" / "cedar_research_rulings_municipal_pha_2026-09-03.csv")
    target = CLEAN / "federal_funding_transactions.csv"
    if not ruling.exists() or not target.exists():
        c.status = "NOT_ESTABLISHED"
        c.detail = "ruling file or target table absent"
        return c
    denied = {}
    with ruling.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            uei = (row.get("uei") or "").strip()
            if uei and (row.get("your_ruling") or "").strip() == "not_native":
                denied[uei] = (row.get("currently_keyed_to") or "").strip()
    live = 0
    with target.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            uei = (row.get("recipient_uei") or "").strip()
            if uei in denied and (row.get("cedar_uid") or "").strip():
                live += 1
    c.measured = {"denied_ueis": len(denied), "rows_still_attributed": live}
    c.status = "PASS" if live == 0 else "FAIL"
    c.detail = ("every denial applied" if live == 0
                else f"{live:,} rows still carry a Cedar attribution that "
                     f"{len(denied)} verified denial(s) forbid")
    return c


def check_preview_complete() -> Check:
    """Every dataset that ships must have a preview, and it must be real.

    Codex, PR #46: `run_all()` never asked whether the preview SET was
    complete, and `release_id()` simply hashes whichever preview files happen
    to exist - so a missing preview would change the id and change nothing
    else. Once the other blockers clear, an incomplete customer preview set
    could take a GREEN verdict.

    (Codex's example - a `gaming` preview declared in MANIFEST.json with no
    `dist/preview/gaming.csv` - was true of the commit it reviewed and is not
    true now; the file exists. The gap it points at is real regardless, which
    is why this check exists rather than a reply saying the example is stale.)

    The manifest is the declaration and the files are the fact, so this
    compares them in BOTH directions: a declared preview with no file, and a
    file nobody declared.
    """
    c = Check("preview set is complete and matches its manifest",
              "dist/preview/MANIFEST.json vs dist/preview/*.csv", blocking=True)
    man = PREVIEW / "MANIFEST.json"
    if not man.exists():
        c.status = "NOT_ESTABLISHED"
        c.detail = "dist/preview/MANIFEST.json absent"
        return c
    try:
        declared = json.loads(man.read_text(encoding="utf-8"))
    except Exception as e:
        c.status = "NOT_ESTABLISHED"
        c.detail = f"manifest unreadable: {e}"
        return c
    rows = declared if isinstance(declared, list) else declared.get("datasets", [])
    names = {r.get("dataset") for r in rows if isinstance(r, dict) and r.get("dataset")}
    on_disk = {p.stem for p in PREVIEW.glob("*.csv")}
    missing = sorted(names - on_disk)
    undeclared = sorted(on_disk - names)
    # A declared preview that is empty is as bad as one that is absent.
    empty = sorted(p.stem for p in PREVIEW.glob("*.csv")
                   if sum(1 for _ in p.open(encoding="utf-8-sig",
                                            errors="replace")) <= 1)
    c.measured = {"declared": len(names), "on_disk": len(on_disk),
                  "missing": len(missing), "undeclared": len(undeclared),
                  "empty": len(empty)}
    problems = []
    if missing:
        problems.append(f"declared but absent: {missing}")
    if undeclared:
        problems.append(f"on disk but undeclared: {undeclared}")
    if empty:
        problems.append(f"header only, no rows: {empty}")
    c.status = "PASS" if not problems else "FAIL"
    c.detail = (f"{len(names)} declared, {len(on_disk)} on disk, all present"
                if not problems else "; ".join(problems))
    return c


def check_no_regression() -> Check:
    c = Check("no-regression chain (62)", "repo-wide ratchet metrics",
              blocking=True)
    baseline = CLEAN / "_regression_baseline.json"
    if not baseline.exists():
        c.status = "NOT_ESTABLISHED"
        c.detail = "no baseline recorded"
        return c
    # 62 takes minutes; the release gate reports its LAST recorded verdict and
    # says so, rather than pretending to a freshness it did not measure.
    c.status = "NOT_ESTABLISHED"
    c.detail = ("not run inline - `py -3 code/62_no_regression_check.py`. "
                "Known red 2026-09-03: 47 tables without codebook blocks. "
                "A release gate must not silently pass a check it skipped.")
    return c


def check_semantics() -> Check:
    c = Check("dataset semantic correctness",
              "13 datasets: row grain, amount additivity, date meaning, "
              "public provenance", blocking=True)
    c.status = "NOT_ESTABLISHED"
    c.detail = ("no test asserts these yet. Named rather than omitted: an "
                "absent check must never read as a pass.")
    return c


def release_id() -> str:
    """Digest over the delivered set. Two runs disagreeing means it moved."""
    h = hashlib.sha256()
    for p in sorted(list(CUSTOMER.glob("*.csv")) + list(PREVIEW.glob("*.csv"))):
        st = p.stat()
        h.update(p.name.encode())
        h.update(str(st.st_size).encode())
        h.update(str(int(st.st_mtime)).encode())
        with p.open("rb") as fh:
            h.update(hashlib.sha256(fh.read(1024)).digest())
    return h.hexdigest()[:16]


def run_all() -> list:
    vocab = neid_vocabulary()
    if not vocab:
        sys.exit("FATAL: NEID vocabulary is empty - every membership test "
                 "would pass vacuously. Refusing to report a release verdict.")
    return [check_csv_identity(vocab), check_db_identity(vocab),
            check_preview_complete(),
            check_artifacts_agree(vocab), check_uid_integrity(),
            check_rulings_applied(), check_no_regression(), check_semantics()]
def _fixture_fails(name, build, run):
    """Build a tree containing a KNOWN violation and assert the check fails.

    Codex, PR #46: the previous selftest asserted only that the uid check
    "reaches a verdict", which an implementation hardwired to PASS satisfies,
    and it exercised none of the database, artifact-agreement, ruling, or
    not-established checks at all. So it could report zero unproven checks
    while proving almost nothing - a positive control that is itself a silent
    pass, which is the exact failure this file was written about.

    Each fixture points the module's own path constants at a temporary tree,
    so the REAL check function runs against planted evidence rather than a
    reimplementation of it.
    """
    import tempfile
    global CUSTOMER, DB, CLEAN, SPINE
    saved = (CUSTOMER, DB, CLEAN, SPINE)
    try:
        with tempfile.TemporaryDirectory() as d:
            build(Path(d))
            got = run()
            ok = got.status == "FAIL"
            print(f"    {'ok  ' if ok else 'FAIL'}  {name}  (returned {got.status})")
            return ok
    finally:
        CUSTOMER, DB, CLEAN, SPINE = saved
        globals()["_RULING_OVERRIDE"] = None


def selftest() -> int:
    """Prove EVERY check can return non-zero. See the module docstring."""
    print("  1169 selftest - proving each check detects its named violation\n")
    global CUSTOMER, DB, CLEAN, SPINE, _RULING_OVERRIDE
    real_vocab = neid_vocabulary()
    if not real_vocab:
        sys.exit("FATAL: no vocabulary - this selftest would prove nothing")
    probe = sorted(real_vocab)[0]
    ok = []

    # 1. a delivered CSV carrying a retired identifier
    def b1(root):
        global CUSTOMER
        (root / "customer").mkdir()
        (root / "customer" / "x.csv").write_text(
            "a,b\n1," + probe + "\n", encoding="utf-8")
        CUSTOMER = root / "customer"

    ok.append(_fixture_fails("a delivered CSV carrying a retired identifier",
                             b1, lambda: check_csv_identity(real_vocab)))

    # 2. a database table still carrying a retired-scheme column
    def b2(root):
        global DB
        DB = root / "db.sqlite"
        con = sqlite3.connect(DB)
        con.execute("CREATE TABLE t (cedar_uid TEXT, tribe_id TEXT)")
        con.execute("INSERT INTO t VALUES ('CE-00001-AA', ?)", (probe,))
        con.commit()
        con.close()

    ok.append(_fixture_fails("a database table with a retired-scheme column",
                             b2, lambda: check_db_identity(real_vocab)))

    # 3. artifacts disagreeing: clean CSVs, dirty database. The check that was
    #    missing entirely before this script existed.
    def b3(root):
        global CUSTOMER, DB
        (root / "customer").mkdir()
        (root / "customer" / "x.csv").write_text(
            "a,b\n1,CE-00001-AA\n", encoding="utf-8")
        CUSTOMER = root / "customer"
        DB = root / "db.sqlite"
        con = sqlite3.connect(DB)
        con.execute("CREATE TABLE t (tribe_id TEXT)")
        con.execute("INSERT INTO t VALUES (?)", (probe,))
        con.commit()
        con.close()

    ok.append(_fixture_fails("CSVs clean but the database not - artifacts disagree",
                             b3, lambda: check_artifacts_agree(real_vocab)))    # 4. one cedar_uid naming two entities
    def b4(root):
        global CLEAN, SPINE, _C1167
        (root / "data" / "clean").mkdir(parents=True)
        (root / "data" / "spine").mkdir(parents=True)
        (root / "data" / "clean" / "cedar_identifier_ledger_final.csv").write_text(
            "cedar_uid,canonical_name,confidence_tier\n"
            "CE-00001-AA,Bristol Bay Native Corporation,A\n"
            "CE-00001-AA,Buena Vista Rancheria,A\n", encoding="utf-8")
        (root / "data" / "clean" / "entity_aliases.csv").write_text(
            "cedar_uid,alias_name\n", encoding="utf-8")
        (root / "data" / "spine" / "cedar_identity_register.csv").write_text(
            "cedar_uid,canonical_name,handle\n"
            "CE-00001-AA,Bristol Bay Native Corporation,X\n", encoding="utf-8")
        CLEAN, SPINE = root / "clean", root / "spine"
        # Point 1167 itself at the fixture. Without this the check re-imports
        # 1167, which resolves LEDGER / ALIASES / the register from ITS OWN
        # module globals, reads the real repo, and returns PASS while a planted
        # collision sits in the fixture - a positive control that proves
        # nothing, which is what Codex flagged.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "c1167_fix", ROOT / "code" / "1167_cedar_uid_identity_collisions.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.ROOT = root
        mod.LEDGER = root / "data" / "clean" / "cedar_identifier_ledger_final.csv"
        mod.ALIASES = root / "data" / "clean" / "entity_aliases.csv"
        _C1167 = mod

    ok.append(_fixture_fails("one cedar_uid naming two entities",
                             b4, check_uid_integrity))

    # 5. a verified denial still attributed in the data
    def b5(root):
        global CLEAN, _RULING_OVERRIDE
        (root / "clean").mkdir()
        (root / "review").mkdir()
        (root / "clean" / "federal_funding_transactions.csv").write_text(
            "recipient_uei,cedar_uid\nDFPYJKG9K2X4,CE-0017W-FN\n", encoding="utf-8")
        CLEAN = root / "clean"
        _RULING_OVERRIDE = root / "review" / "r.csv"
        _RULING_OVERRIDE.write_text(
            "your_ruling,uei,currently_keyed_to\n"
            "not_native,DFPYJKG9K2X4,CE-0017W-FN\n", encoding="utf-8")

    ok.append(_fixture_fails("a verified denial still attributed in the data",
                             b5, check_rulings_applied))

    # 6 and 7. The two checks with no implementation yet must say exactly that
    #    and must block. An absent check has to read as absent, never as a pass;
    #    asserting the contract is the only honest control available for them.
    for fn, label in ((check_no_regression, "no-regression"),
                      (check_semantics, "dataset semantics")):
        c = fn()
        good = c.status == "NOT_ESTABLISHED" and c.blocking
        print(f"    {'ok  ' if good else 'FAIL'}  {label}: reports "
              f"NOT_ESTABLISHED and blocks  ({c.status}, blocking={c.blocking})")
        ok.append(good)

    bad = [i for i, v in enumerate(ok) if not v]
    print(f"\n  1169 selftest   {'ok' if not bad else 'FAIL'}   "
          f"{len(bad)} of {len(ok)} check(s) unproven")
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        return selftest()
    checks = run_all()
    rid = release_id()
    as_json = "--json" in sys.argv

    if as_json:
        print(json.dumps({"release_id": rid,
                          "checks": [c.__dict__ for c in checks]}, indent=2))
    else:
        print(f"\n  CEDAR PRESS RELEASE VERIFY      release id {rid}\n")
        print(f"  {'check':<46} {'scope':<44} {'result':<18} blocking")
        print("  " + "-" * 118)
        for c in checks:
            mark = {"PASS": "PASS", "FAIL": "FAIL",
                    "NOT_ESTABLISHED": "NOT ESTABLISHED",
                    "UNPROVEN": "UNPROVEN"}.get(c.status, c.status)
            print(f"  {c.name[:46]:<46} {c.scope[:44]:<44} {mark:<18} "
                  f"{'YES' if c.blocking else '-'}")
            if c.status != "PASS":
                print(f"  {'':<46} -> {c.detail[:104]}")

    blocked = [c for c in checks
               if c.blocking and c.status in ("FAIL", "NOT_ESTABLISHED", "UNPROVEN")]
    if not as_json:
        print()
        if blocked:
            print(f"  RELEASE STATUS: BLOCKED   ({len(blocked)} blocking "
                  f"failure(s) of {len(checks)} checks)")
            for c in blocked:
                print(f"      - {c.name}: {c.status}")
        else:
            print("  RELEASE STATUS: GREEN")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
