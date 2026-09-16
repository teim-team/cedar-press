#!/usr/bin/env python3
"""Tests for code/1188_import_chatgpt_r7_business_register.py.

Imports the production module and exercises its real functions. Uses temporary
directories only: never the real audit store, never canonical data. Includes
independent-subprocess lock tests and a git line-ending round trip.

    py -3 -B code/1188_import_chatgpt_r7_business_register_test.py

POS = positive control; NEG = negative fixture (one condition changed from a valid
input, and the production path must reject, downgrade or refuse it).
"""
import copy
import contextlib
import csv
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import warnings
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("r7audit", Path(__file__).with_name("1188_import_chatgpt_r7_business_register.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules["r7audit"] = M
_spec.loader.exec_module(M)
globals().update({k: v for k, v in vars(M).items() if not k.startswith("__") and k not in ("sys", "os", "json")})


def run_tests():
    """Assertions against production functions. POS = positive control (valid input
    behaves correctly); NEG = negative fixture (one condition changed from a valid
    input; the production path must reject, downgrade or refuse it)."""
    ident = ident_module()
    base = load()
    today = date.today()
    results, used = [], set()

    def check(kind, label, ok, uses, detail=""):
        results.append((kind, label, bool(ok)))
        used.update(uses)
        print(f"  {kind} {label:<84} {'OK' if ok else 'FAILED'} {detail}"[:260])

    NB = (True, "no current audit bundle yet")

    def clone(*names, **over):
        t = dict(base)
        t["raw"] = dict(base["raw"])
        for n in names:
            t["raw"][n] = copy.deepcopy(base["raw"][n])
        t.update(over)
        return t

    def integ(t):
        return {c: ok for c, ok, _ in integrity(t, NB)[0]}

    def set_cell(t, name, key_col, key, column, value):
        h = t["raw"][name]["header"]
        for r in t["raw"][name]["rows"]:
            if r[h.index(key_col)] == key:
                r[h.index(column)] = value

    I = ("load", "integrity")
    # ---------------------------------------------------------------- integrity
    check("POS", "real inputs: all 12 integrity checks pass", all(integ(base).values()), I)
    check("NEG", "wrong ZIP hash fails I01", not integ(clone(zip_sha="0" * 64))["I01"], I)
    with tempfile.TemporaryDirectory() as d, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        members = {f: zipfile.ZipFile(base["paths"].zip).read(EXPECTED_PREFIX + f) for f in FILES}

        def build_zip(name, extra=()):
            zp = Path(d) / name
            with zipfile.ZipFile(zp, "w") as z:
                for f, blob in members.items():
                    z.writestr(EXPECTED_PREFIX + f, blob)
                for member, blob in extra:
                    z.writestr(member, blob)
            return zp
        check("POS", "real ZIP on disk with the 13 exact members passes I03",
              integ(load(replace(PROD, zip=build_zip("ok.zip"))))["I03"], I + ("select_members",))
        check("NEG", "real ZIP on disk with a duplicate member name fails I03",
              not integ(load(replace(PROD, zip=build_zip("dup.zip", [(EXPECTED_PREFIX + REG, members[REG])]))))["I03"],
              I + ("select_members",))
        check("NEG", "real ZIP on disk with an ambiguous nested path fails I03",
              not integ(load(replace(PROD, zip=build_zip("amb.zip", [("copy/" + R7_DIR + REG, members[REG])]))))["I03"],
              I + ("select_members",))
    t = clone(REG); t["raw"][REG]["header"] = [c if c != "business_name" else "name_x" for c in t["raw"][REG]["header"]]
    check("NEG", "missing required header fails I04", not integ(t)["I04"], I)
    t = clone(ACT); t["raw"][ACT]["rows"][0] = t["raw"][ACT]["rows"][0][:-1]
    check("NEG", "ragged row fails I04", not integ(t)["I04"], I)
    t = clone(ENT); t["raw"][ENT]["rows"].append(list(t["raw"][ENT]["rows"][0]))
    check("NEG", "duplicate CE row in the R7 register fails I05", not integ(t)["I05"], I)
    t = clone("live:register"); t["raw"]["live:register"]["rows"].append(list(t["raw"]["live:register"]["rows"][3]))
    check("NEG", "duplicate CE row in the live register fails I05", not integ(t)["I05"], I)
    t = clone(REG); t["raw"][REG]["rows"].append(list(t["raw"][REG]["rows"][0]))
    check("NEG", "duplicate CB row in the issued register fails I06", not integ(t)["I06"], I)
    t = clone(ACT); set_cell(t, ACT, "business_uid", "CB-1000001", "business_name", "A DIFFERENT NAME LLC")
    check("NEG", "issued/active shared field contradiction fails I07", not integ(t)["I07"], I)
    t = clone(LIN); t["raw"][LIN]["rows"].append(list(t["raw"][LIN]["rows"][0]))
    check("NEG", "duplicate retirement mapping fails I08", not integ(t)["I08"], I)
    rel_t = "registries/Business_Native_Relationships.csv"
    t = clone(rel_t); t["raw"][rel_t]["rows"][0][t["raw"][rel_t]["header"].index("business_uid")] = "CB-9999998"
    check("NEG", "unresolved business reference fails I09", not integ(t)["I09"], I)
    t = clone(rel_t); t["raw"][rel_t]["rows"][0][t["raw"][rel_t]["header"].index("cedar_uid")] = "CB-1000001"
    check("NEG", "CB id in an entity column fails I10", not integ(t)["I10"], I)
    par = "registries/Business_Parent_Business_Relationships.csv"
    t = clone(par); t["raw"][par]["rows"][0][t["raw"][par]["header"].index("parent_business_uid")] = "CE-00134-BX"
    check("NEG", "CE id in a business column fails I10", not integ(t)["I10"], I)
    t = clone(REG, ACT)
    for n in (REG, ACT):
        set_cell(t, n, "business_uid", "CB-1000001", "business_name", " ")
    check("NEG", "nameless business fails I11", not integ(t)["I11"], I)
    t_tiny = clone(REG, ACT)
    for n in (REG, ACT):
        set_cell(t_tiny, n, "business_uid", "CB-1015175", "dataset_membership", "NEED")
    check("NEG", "reverting the Tiny Tots correction fails I12", not integ(t_tiny)["I12"], I)

    # ---------------------------------------------------------------- URLs and evidence grading
    U = ("classify_url",)
    check("POS", "record-level https URL is valid", classify_url("https://www.olgoonik.com/what-we-do/subsidiaries/") == URL_VALID, U)
    for label, value, note, want in [("bare 'https://'", "https://", "", "INVALID"),
                                     ("malformed 'htps//example.org/x'", "htps//example.org/x", "", "INVALID"),
                                     ("host without a dot", "https://localhost/record", "", "INVALID"),
                                     ("Windows local path", "C:\\evidence\\report.pdf", "", "LOCAL_PATH"),
                                     ("blank", "", "", "MISSING"),
                                     ("search homepage", "https://search.certifications.sba.gov/", "", "HOST_ROOT_ONLY"),
                                     ("valid URL with an integrity note", "https://www.olgoonik.com/x", "was a local path",
                                      "DOWNGRADED_BY_INTEGRITY_NOTE")]:
        check("NEG", f"URL {label} is {want}", classify_url(value, note) == want, U)
    ce, name = "CE-0007J-FJ", "Afognak Native Corporation"
    clean = {c: "" for c in LIVE_REQUIRED["ledger"]}
    clean.update(identifier_type="UEI", identifier="X", cedar_uid=ce, legal_business_name=name, confidence_tier="A",
                 method_quarantined="N", attribution_method="agent_research_two_leg",
                 evidence_url="https://www.example.org/filings/afognak")
    G = ("grade_ledger_row", "assess_pair", "classify_url")
    check("POS", "clean tier A row, valid URL, registrant name matches -> candidate only",
          assess_pair({("UEI", "X")}, [clean], ce, name) == CANDIDATE, G)
    for label, change, want in [
            ("quarantined (all else clean)", {"method_quarantined": "Y", "quarantine_disposition": "KEEP"}, WEAK),
            ("tier B (all else clean)", {"confidence_tier": "B"}, WEAK),
            ("withdrawn (all else clean)", {"quarantine_disposition": "WITHDRAW"}, WEAK),
            ("subsidiary registrant name", {"legal_business_name": name + " Services LLC"}, WEAK),
            ("evidence URL 'https://'", {"evidence_url": "https://"}, WEAK),
            ("evidence URL malformed", {"evidence_url": "https:/example.org"}, WEAK),
            ("evidence URL is a homepage", {"evidence_url": "https://www.example.org/"}, WEAK),
            ("attributed to another entity", {"cedar_uid": "CE-00134-BX"}, CONFLICT),
            ("excluded by ruling", {"exclusion_id": "EXCL-1"}, "ATTRIBUTION_REFUTED_OR_EXCLUDED")]:
        check("NEG", f"evidence: {label} -> {want}", assess_pair({("UEI", "X")}, [dict(clean, **change)], ce, name) == want, G)

    # ---------------------------------------------------------------- real evaluation
    E = ("evaluate", "pair_views", "queue_rows", "gates", "exit_code", "ledger_measurements")
    ev0 = evaluate(base, NB, {}, ident, today)
    lm = ledger_measurements(ev0["views"])
    check("POS", "real data: 83 proposed pairs, all UNRESOLVED without decisions",
          len(ev0["rows"]) == 83 and all(r["resolution_status"] == "UNRESOLVED" for r in ev0["rows"]), E)
    check("POS", "real data: candidate evidence 0, weak or insufficient 60",
          lm["generated_assessment"].get(CANDIDATE, 0) == 0 and lm["generated_assessment"].get(WEAK) == 60, E)
    check("POS", "real data: integrity PASS but NOT_APPROVED exits 10", exit_code(ev0) == EXIT_NOT_APPROVED, E)

    # ---------------------------------------------------------------- decisions
    D = ("load_decisions",)
    views = ev0["views"]
    vp = next(v for v in views if v["rows"])
    keys = {v["key"] for v in views}

    def gate_rec(did, status="APPROVED", sup=None):
        return {"decision_id": did, "status": status, "value": "test value", "decided_by": "owner",
                "decided_on": "2026-09-14", "basis": "test basis", "supersedes": sup}

    def pair_rec(did, v, disp="CONFIRMED_SAME_LEGAL_OBJECT", sup=None, fp=None):
        return {"decision_id": did, "cedar_uid": v["ce"], "business_uid": v["cb"], "disposition": disp,
                "evidence_fingerprint": fp or v["fingerprint"], "decided_by": "owner", "decided_on": "2026-09-14",
                "basis": "cage.dla.mil lookup", "supersedes": sup}
    valid = {"schema": DECISIONS_SCHEMA,
             "gates": {"cb_id_format": [gate_rec("g1")], "business_name_publication": [gate_rec("g2")],
                       "ship_bars": [gate_rec("g3")]},
             "proposed_equivalence_pairs": [pair_rec("p1", vp)]}

    def dec(dobj, prior=None):
        return load_decisions(json.dumps(dobj).encode("utf-8"), views, today, prior)
    st_v, err_v = dec(valid)
    check("POS", "valid decisions file: no errors, pair CURRENT, three gate heads",
          not err_v and st_v["pairs"][vp["key"]]["status"] == "CURRENT" and len(st_v["gate_heads"]) == 3, D)

    def mutated(fn):
        dd = copy.deepcopy(valid)
        fn(dd)
        return dec(dd)[1]
    for label, fn in [
            ("gate status 'false'", lambda dd: dd["gates"]["cb_id_format"][0].update(status="false")),
            ("gate status 'true'", lambda dd: dd["gates"]["cb_id_format"][0].update(status="true")),
            ("gate status boolean true", lambda dd: dd["gates"]["cb_id_format"][0].update(status=True)),
            ("blank decided_by", lambda dd: dd["gates"]["ship_bars"][0].update(decided_by=" ")),
            ("impossible date", lambda dd: dd["proposed_equivalence_pairs"][0].update(decided_on="2026-13-01")),
            ("future date 2099-01-01", lambda dd: dd["proposed_equivalence_pairs"][0].update(decided_on="2099-01-01")),
            ("unknown key", lambda dd: dd["proposed_equivalence_pairs"][0].update(approved=True)),
            ("disposition 'yes'", lambda dd: dd["proposed_equivalence_pairs"][0].update(disposition="yes")),
            ("malformed CE", lambda dd: dd["proposed_equivalence_pairs"][0].update(cedar_uid="CE-1")),
            ("malformed fingerprint", lambda dd: dd["proposed_equivalence_pairs"][0].update(evidence_fingerprint="abc")),
            ("duplicate decision_id", lambda dd: dd["gates"]["ship_bars"][0].update(decision_id="g1")),
            ("two heads for one pair (fork)", lambda dd: dd["proposed_equivalence_pairs"].append(pair_rec("p9", vp))),
            ("supersedes an unknown decision", lambda dd: dd["proposed_equivalence_pairs"][0].update(supersedes="nope")),
            ("old schema version", lambda dd: dd.update(schema="cedar.r7.owner_decisions.v1"))]:
        check("NEG", f"decisions rejected: {label}", bool(mutated(fn)), D)
    raw_dup = b'{"schema": "cedar.r7.owner_decisions.v2", "gates": {}, "gates": {}, "proposed_equivalence_pairs": []}'
    check("NEG", "decisions rejected: duplicate JSON key", bool(load_decisions(raw_dup, views, today)[1]), D)
    hist = copy.deepcopy(valid)
    hist["proposed_equivalence_pairs"].append(dict(pair_rec("p_other", vp), cedar_uid="CE-00134-BX", business_uid="CB-1000001"))
    st_h, err_h = dec(hist)
    check("POS", "well-formed decision for a pair R7 does not propose is HISTORICAL and resolves nothing",
          not err_h and st_h["counts"]["historical"] == 1 and "CE-00134-BX|CB-1000001" not in st_h["pairs"], D)
    later = copy.deepcopy(valid)
    later["proposed_equivalence_pairs"].append(pair_rec("p2", vp, "REFUSED_NOT_SAME_LEGAL_OBJECT", sup="p1"))
    st_l, err_l = dec(later)
    check("POS", "a later decision supersedes: head REFUSED and CURRENT, prior kept as SUPERSEDED",
          not err_l and st_l["pairs"][vp["key"]]["record"]["decision_id"] == "p2"
          and st_l["counts"]["superseded"] == 1 and set(st_l["records"]) >= {"p1", "p2"}, D)
    removed = copy.deepcopy(valid)
    removed["proposed_equivalence_pairs"] = []
    check("NEG", "removing a decision the current bundle recorded is rejected (append-only)",
          bool(dec(removed, st_v["records"])[1]), D)
    target = vp["rows"][0]
    t_chg = clone("live:ledger", decisions_bytes=json.dumps(valid).encode())
    h = t_chg["raw"]["live:ledger"]["header"]
    for r in t_chg["raw"]["live:ledger"]["rows"]:
        if dict(zip(h, r)) == target:
            r[h.index("verified_date")] = "1999-01-01"
    ev_cur = evaluate(dict(base, decisions_bytes=json.dumps(valid).encode()), NB, {}, ident, today)
    ev_chg = evaluate(t_chg, NB, {}, ident, today)
    row_cur = next(r for r in ev_cur["rows"] if r["pair_key"] == vp["key"])
    row_chg = next(r for r in ev_chg["rows"] if r["pair_key"] == vp["key"])
    check("POS", "decision bound to the reviewed fingerprint is CURRENT (OWNER_CONFIRMED)",
          row_cur["resolution_status"] == "OWNER_CONFIRMED" and row_cur["decision_status"] == "CURRENT", E + D)
    check("NEG", "same CE/CB pair, changed ledger evidence -> decision STALE, pair UNRESOLVED",
          row_chg["decision_status"] == "STALE" and row_chg["resolution_status"] == "UNRESOLVED_STALE_DECISION"
          and ev_chg["decisions"]["counts"]["stale"] == 1, E + D)

    # ---------------------------------------------------------------- notes (commentary, never gates)
    N = ("load_notes",)

    def note(k, text="checked cage.dla.mil", on="2026-09-14"):
        return {"pair_key": k, "note": text, "updated_by": "owner", "updated_on": on}
    notes_ok = {"schema": NOTES_SCHEMA, "notes": [note(vp["key"])],
                "historical_notes": [note("CE-00134-BX|CB-1000001", "pair no longer proposed")]}
    nst, nerr = load_notes(json.dumps(notes_ok).encode(), keys, today)
    check("POS", "valid notes file: one note, one historical note for a pair no longer proposed",
          not nerr and vp["key"] in nst["notes"] and "CE-00134-BX|CB-1000001" in nst["historical"], N)
    for label, fn in [("malformed pair_key", lambda x: x["notes"][0].update(pair_key="CE-1|CB-2")),
                      ("duplicate pair_key", lambda x: x["notes"].append(note(vp["key"], "again"))),
                      ("unexpected future field", lambda x: x["notes"][0].update(priority="high")),
                      ("unexpected top-level field", lambda x: x.update(version=2)),
                      ("future updated_on", lambda x: x["notes"][0].update(updated_on="2099-01-01")),
                      ("blank note text", lambda x: x["notes"][0].update(note=" ")),
                      ("note on a pair that is not proposed", lambda x: x["notes"].append(note("CE-00134-BX|CB-1000002"))),
                      ("historical note for a pair still proposed",
                       lambda x: x["historical_notes"].append(note(sorted(keys - {vp['key']})[0])))]:
        nn = copy.deepcopy(notes_ok)
        fn(nn)
        check("NEG", f"notes rejected: {label}", bool(load_notes(json.dumps(nn).encode(), keys, today)[1]), N)
    check("NEG", "notes rejected: duplicate JSON key",
          bool(load_notes(b'{"schema": "cedar.r7.owner_notes.v1", "notes": [], "notes": [], "historical_notes": []}', keys, today)[1]), N)
    ev_n = evaluate(dict(base, decisions_bytes=json.dumps(valid).encode(), notes_bytes=json.dumps(notes_ok).encode()),
                    NB, {}, ident, today)
    row_n = next(r for r in ev_n["rows"] if r["pair_key"] == vp["key"])
    check("POS", "a note never changes decision status or gates",
          row_n["resolution_status"] == row_cur["resolution_status"] and row_n["decision_status"] == "CURRENT"
          and row_n["owner_note_snapshot"] == "checked cage.dla.mil"
          and [(c, o) for c, o, _ in ev_n["gates"]] == [(c, o) for c, o, _ in ev_cur["gates"]], E + N)
    ev_ln = evaluate(dict(base, decisions_bytes=json.dumps(later).encode(), notes_bytes=json.dumps(notes_ok).encode()),
                     NB, {}, ident, today)
    row_ln = next(r for r in ev_ln["rows"] if r["pair_key"] == vp["key"])
    check("POS", "a decision change never erases a note",
          row_ln["resolution_status"] == "OWNER_REFUSED" and row_ln["owner_note_snapshot"] == "checked cage.dla.mil", E + N)

    # ---------------------------------------------------------------- approval matrix
    full = copy.deepcopy(valid)
    full["proposed_equivalence_pairs"] = [pair_rec(f"all{i}", v) for i, v in enumerate(views)]
    fb = json.dumps(full).encode()
    ev_ok = evaluate(dict(base, decisions_bytes=fb, writer_publishes_names=True), NB, {}, ident, today)
    check("POS", "every decision CURRENT + live policy publishes -> APPROVED, exit 0",
          ev_ok["approval"] == "APPROVED" and exit_code(ev_ok) == 0, E + D)
    ev_w = evaluate(dict(base, decisions_bytes=fb, writer_publishes_names=False), NB, {}, ident, today)
    check("NEG", "live policy still withholds names -> G05 BLOCKED, exit 10",
          not dict((c, o) for c, o, _ in ev_w["gates"])["G05"] and exit_code(ev_w) == EXIT_NOT_APPROVED, E + D)
    ev_bad = evaluate(dict(t_tiny, decisions_bytes=fb, writer_publishes_names=True), NB, {}, ident, today)
    check("NEG", "every decision recorded but integrity FAIL -> NOT_APPROVED, exit 1",
          ev_bad["approval"] == "NOT_APPROVED" and exit_code(ev_bad) == 1, E + D)
    bad_notes = dict(notes_ok, notes=[note("CE-00134-BX|CB-1000002")])
    ev_bn = evaluate(dict(base, decisions_bytes=fb, writer_publishes_names=True, notes_bytes=json.dumps(bad_notes).encode()),
                     NB, {}, ident, today)
    check("NEG", "invalid notes file -> NOT_APPROVED, exit 1, even with every decision recorded",
          ev_bn["approval"] == "NOT_APPROVED" and exit_code(ev_bn) == 1, E + N)

    # ---------------------------------------------------------------- store: immutable bundles, external notes
    S = ("freeze", "prepare", "read_store", "activate", "build_manifest", "validate_manifest", "transaction_lock", "load_notes")
    X = ("transaction_lock", "lock_held", "freeze", "recover", "load_verified", "input_snapshot", "report", "inventory", "read_store")
    real_write, real_replace = M._write_new, os.replace

    def paths_in(d):
        return replace(PROD, decisions=d / "decisions.json", notes=d / "notes.json", audit_dir=d / "audit")

    def T(pth):
        return refresh_decisions(dict(base, paths=pth))

    def cur(pth):
        return (pth.audit_dir / "CURRENT.json").read_bytes()

    def files_of(pth, bid):
        d = pth.audit_dir / "bundles" / bid
        return (d / "manifest.json").read_bytes(), (d / "queue.csv").read_bytes()

    def refused(fn, exc=Refused):
        try:
            fn()
        except exc:
            return True
        return False

    def write_notes(pth, entries):
        pth.notes.write_bytes(json.dumps({"schema": NOTES_SCHEMA, "notes": entries, "historical_notes": []}).encode())

    def quiet_report(pth, cached=base):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = report(pth, ident, cached=cached)
        return code, buf.getvalue()

    def quiet_code(pth):
        return quiet_report(pth)[0]

    def qrows(pth):
        return {r["pair_key"]: r for r in dicts(parse_csv(read_store(pth)["queue_bytes"]))}

    with tempfile.TemporaryDirectory() as d:
        pth = paths_in(Path(d))
        write_notes(pth, [])
        _, bid_a, how = freeze(pth, ident, today, cached=base)
        st = read_store(pth)
        check("POS", "first freeze: activated, CLEAN, 83 UNRESOLVED rows, no lock left behind",
              how == "activated" and st["state"] == "CLEAN" and len(qrows(pth)) == 83 and not lock_held(pth), S)
        check("POS", "the bundle manifest is structurally valid, internally consistent and reproduces",
              not any(validate_manifest(st["manifest"], T(pth), st["queue_bytes"]).values()), S)
        a_files = files_of(pth, bid_a)
        write_notes(pth, [note(vp["key"])])
        _, bid_b, _ = freeze(pth, ident, today, cached=base)
        check("POS", "note added in the external notes file -> a new bundle snapshots it",
              bid_b != bid_a and qrows(pth)[vp["key"]]["owner_note_snapshot"] == "checked cage.dla.mil", S)
        write_notes(pth, [])
        _, bid_c, how_c = freeze(pth, ident, today, cached=base)
        hist = read_store(pth)["pointer"]["activated_bundles"]
        check("POS", "note removed -> exact return to the earlier bundle id, reactivated, its files byte-identical",
              bid_c == bid_a and how_c == "reactivated" and files_of(pth, bid_a) == a_files and bid_b in hist, S)
        write_notes(pth, [note(vp["key"])])
        freeze(pth, ident, today, cached=base)
        fp = qrows(pth)[vp["key"]]["evidence_fingerprint"]
        d1 = {"schema": DECISIONS_SCHEMA, "gates": {}, "proposed_equivalence_pairs": [pair_rec("p1", vp, fp=fp)]}
        pth.decisions.write_bytes(json.dumps(d1).encode())
        _, bid_d, _ = freeze(pth, ident, today, cached=base)
        rd = qrows(pth)[vp["key"]]
        check("POS", "first valid decision -> OWNER_CONFIRMED; the note is kept",
              rd["resolution_status"] == "OWNER_CONFIRMED" and rd["owner_note_snapshot"] == "checked cage.dla.mil", S + D)
        d2 = copy.deepcopy(d1)
        d2["proposed_equivalence_pairs"].append(pair_rec("p2", vp, "REFUSED_NOT_SAME_LEGAL_OBJECT", sup="p1", fp=fp))
        pth.decisions.write_bytes(json.dumps(d2).encode())
        freeze(pth, ident, today, cached=base)
        m2 = read_store(pth)["manifest"]
        m_d = json.loads(files_of(pth, bid_d)[0])
        check("POS", "later decision -> OWNER_REFUSED, p1 SUPERSEDED, note kept, earlier bundle still shows the old decision",
              qrows(pth)[vp["key"]]["resolution_status"] == "OWNER_REFUSED" and m2["decisions"]["counts"]["superseded"] == 1
              and qrows(pth)[vp["key"]]["owner_note_snapshot"] == "checked cage.dla.mil"
              and m_d["queue"]["rendered"][vp["key"]]["owner_disposition"] == "CONFIRMED_SAME_LEGAL_OBJECT", S + D)
        before = cur(pth)
        pth.decisions.write_bytes(json.dumps(d1).encode())
        check("NEG", "decision history rewritten (p2 removed) -> freeze refused, CURRENT unchanged, lock released",
              refused(lambda: freeze(pth, ident, today, cached=base)) and cur(pth) == before and not lock_held(pth), S + D)
        pth.decisions.write_bytes(json.dumps(d2).encode())
        write_notes(pth, [note(vp["key"]), note("CE-00134-BX|CB-1000002", "pair no longer proposed")])
        check("NEG", "note left under notes for a pair that is not proposed -> freeze refused", refused(lambda: freeze(pth, ident, today, cached=base)), S)
        pth.notes.write_bytes(json.dumps({"schema": NOTES_SCHEMA, "notes": [note(vp["key"]), note(vp["key"], "twice")],
                                          "historical_notes": []}).encode())
        check("NEG", "duplicate note key -> freeze refused, CURRENT unchanged",
              refused(lambda: freeze(pth, ident, today, cached=base)) and cur(pth) == before, S)
        write_notes(pth, [note(vp["key"])])

        # ---------------------------------------------------------------- every generated-queue edit is detected
        st = read_store(pth)
        bid_cur, m_cur, q_cur = st["pointer"]["bundle_id"], st["manifest"], st["queue_bytes"]
        qpath = pth.audit_dir / "bundles" / bid_cur / "queue.csv"
        rows0 = dicts(parse_csv(q_cur))
        other = next(i for i, r in enumerate(rows0) if r["pair_key"] != vp["key"])

        def set_field(field, value, i=0):
            def fn(rows):
                rows[i][field] = value
            return fn

        def swap(rows):
            rows[0], rows[1] = rows[1], rows[0]

        def dup(rows):
            rows.append(dict(rows[0]))
        for label, fn in [("business_name", set_field("business_name", "EDITED LLC")),
                          ("entity_name", set_field("entity_name", "Edited Corporation")),
                          ("cedar_uid", set_field("cedar_uid", "CE-00134-BX")),
                          ("evidence_urls", set_field("evidence_urls", "https://www.example.org/forged")),
                          ("generated_assessment", set_field("generated_assessment", CANDIDATE)),
                          ("evidence_fingerprint", set_field("evidence_fingerprint", "f" * 64)),
                          ("supporting_ledger_rows_json", set_field("supporting_ledger_rows_json", "[]")),
                          ("owner_disposition", set_field("owner_disposition", "CONFIRMED_SAME_LEGAL_OBJECT", other)),
                          ("owner_note_snapshot", set_field("owner_note_snapshot", "forged note", other)),
                          ("row order", swap), ("duplicate row", dup)]:
            rows = copy.deepcopy(rows0)
            fn(rows)
            qpath.write_bytes(queue_to_bytes(rows))
            try:
                corrupt = bid_cur in read_store(pth)["corrupt"]
                code = quiet_code(pth)
                blocked = refused(lambda: freeze(pth, ident, today, cached=base))
            finally:
                qpath.write_bytes(q_cur)
            check("NEG", f"bundle edit detected ({label}): CORRUPT, report exit 4, freeze refused",
                  corrupt and code == EXIT_CORRUPT and blocked, S + ("report",))
            if label in ("evidence_fingerprint", "owner_disposition", "owner_note_snapshot", "row order", "duplicate row"):
                tb = queue_to_bytes(rows)
                mm = copy.deepcopy(m_cur)
                mm["queue"]["sha256"] = sha256_bytes(tb)
                check("NEG", f"even with a matching queue hash, the manifest's meaning rejects the {label} edit",
                      bool(validate_manifest(mm, queue_bytes=tb)["SEMANTIC_INVALID"]), ("validate_manifest",))
        check("POS", "restored bundle is intact again", read_store(pth)["state"] == "CLEAN", S)

        # ---------------------------------------------------------------- report holds the lock for its whole snapshot
        R = ("report", "transaction_lock", "load_verified", "read_store")
        code_ok, out_ok = quiet_report(pth)
        check("POS", "unlocked report: integrity PASS, NOT_APPROVED, exit 10, current bundle reproduces",
              code_ok == EXIT_NOT_APPROVED and "INTEGRITY: PASS" in out_ok and "IMPORT APPROVAL: NOT_APPROVED" in out_ok
              and "reproduces from current inputs" in out_ok, R)
        for holder in ("freeze", "recover"):
            with transaction_lock(pth, holder):
                code_l, out_l = quiet_report(pth)
            check("NEG", f"report while {holder} holds the lock: refuses with exit 5, claims neither incompleteness nor corruption",
                  code_l == EXIT_LOCKED and "LOCK:" in out_l and "INCOMPLETE" not in out_l and "CORRUPT" not in out_l, R)
        check("POS", "the lock is free once the holder finishes, and the report reads again", quiet_code(pth) == EXIT_NOT_APPROVED, R)
        write_notes(pth, [note(vp["key"], "changed before the report acquires the lock")])
        code_n, out_n = quiet_report(pth)
        check("POS", "owner input changed immediately before the report: the report loads the new state under the lock",
              "1 notes" in out_n and code_n == EXIT_NOT_APPROVED, R)
        HOOKS["report_after_snapshot"] = lambda p: write_notes(pth, [note(vp["key"], "changed after the report acquired the lock")])
        try:
            code_d, out_d = quiet_report(pth)
        finally:
            HOOKS.clear()
        check("NEG", "owner input changed after the report acquired the lock: stale-snapshot exit, never 10",
              "SNAPSHOT STALE: inputs changed while the report ran; rerun required (notes)" in out_d
              and code_d == EXIT_SNAPSHOT_STALE and code_d != EXIT_NOT_APPROVED, R)
        check("POS", "the output distinguishes a stale bundle artifact from a stale report snapshot",
              "SNAPSHOT STALE" in out_d and "IS NOT CURRENT" in out_d
              and "SNAPSHOT STALE" not in out_ok and "BUNDLE " in out_ok, R)
        check("POS", "the report records nothing: no owner metadata is written while it holds the lock",
              not (pth.audit_dir / ".lock.owner.json").exists() or json.loads(
                  (pth.audit_dir / ".lock.owner.json").read_text(encoding="utf-8"))["operation"] != "report", R)
        write_notes(pth, [note(vp["key"])])
        freeze(pth, ident, today, cached=base)

        # ------------------------------------------- a stale snapshot overrides an APPROVED evaluation
        ST = ("report", "exit_code", "changed_inputs", "read_lock")
        real_evaluate = M.evaluate

        def approving(*a, **k):
            return dict(real_evaluate(*a, **k), approval="APPROVED", integrity_pass=True,
                        decision_errors=[], notes_errors=[])

        M.evaluate = approving
        try:
            code_a, out_a = quiet_report(pth)
            HOOKS["report_after_snapshot"] = lambda p: write_notes(pth, [note(vp["key"], "changed under the lock")])
            try:
                code_ad, out_ad = quiet_report(pth)
            finally:
                HOOKS.clear()
        finally:
            M.evaluate = real_evaluate
            write_notes(pth, [note(vp["key"])])
        check("POS", "no drift + APPROVED evaluation: exit 0", code_a == 0 and "IMPORT APPROVAL: APPROVED" in out_a, ST)
        check("NEG", "APPROVED evaluation + drift: stale-snapshot exit, never 0",
              code_ad == EXIT_SNAPSHOT_STALE and code_ad != 0 and "IS NOT CURRENT" in out_ad
              and "SNAPSHOT STALE: inputs changed while the report ran; rerun required" in out_ad, ST)

        # ------------------------------------------- report creates nothing, even on a store that does not exist
        FS = ("report", "read_lock")

        def tree(root):
            """Directory inventory: every entry, its mtime and its content hash. A file
            whose byte range is locked cannot be read, and size plus mtime still show
            whether anything was written to it."""
            root, out = Path(root), {}
            if root.exists():
                for q in sorted(root.rglob("*")):
                    if q.is_dir():
                        out[q.relative_to(root).as_posix()] = "dir"
                        continue
                    stq = q.stat()
                    try:
                        mark = sha256_bytes(q.read_bytes())
                    except PermissionError:
                        mark = f"locked:{stq.st_size}"
                    out[q.relative_to(root).as_posix()] = f"{stq.st_mtime_ns}:{mark}"
            return out

        with tempfile.TemporaryDirectory() as d2:
            fresh = paths_in(Path(d2))
            b0 = tree(d2)
            c0, o0 = quiet_report(fresh)
            check("NEG", "no audit directory: report refuses as uninitialized and creates nothing",
                  c0 == EXIT_NO_STORE and "AUDIT STORE NOT INITIALIZED" in o0
                  and not fresh.audit_dir.exists() and tree(d2) == b0, FS)
            fresh.audit_dir.mkdir(parents=True)
            b1 = tree(d2)
            c1, o1 = quiet_report(fresh)
            check("NEG", "audit directory but no lock file: report refuses and creates no lock file",
                  c1 == EXIT_NO_STORE and "AUDIT STORE NOT INITIALIZED" in o1
                  and not lock_path(fresh).exists() and tree(d2) == b1, FS)
            lock_path(fresh).write_bytes(b"")
            b2 = tree(d2)
            c2, o2 = quiet_report(fresh)
            check("NEG", "lock file but no CURRENT: report refuses without creating a store",
                  c2 == EXIT_NO_STORE and "AUDIT STORE NOT INITIALIZED" in o2
                  and not (fresh.audit_dir / "CURRENT.json").exists()
                  and not (fresh.audit_dir / "bundles").exists() and tree(d2) == b2, FS)
        t4 = tree(pth.audit_dir)
        c4, o4 = quiet_report(pth)
        check("POS", "initialized store: report reads under the existing lock and changes no file, mtime or entry",
              c4 == EXIT_NOT_APPROVED and tree(pth.audit_dir) == t4, FS)
        with transaction_lock(pth, "freeze"):
            t5 = tree(pth.audit_dir)
            c5, o5 = quiet_report(pth)
            same5 = tree(pth.audit_dir) == t5
        check("NEG", "lock held: report exits 5 and writes nothing", c5 == EXIT_LOCKED and same5, FS)
        HOOKS["report_after_snapshot"] = lambda p: write_notes(pth, [note(vp["key"], "drift")])
        try:
            t6 = tree(pth.audit_dir)
            c6, o6 = quiet_report(pth)
            same6 = tree(pth.audit_dir) == t6
        finally:
            HOOKS.clear()
            write_notes(pth, [note(vp["key"])])
        check("NEG", "snapshot drift: stale-snapshot exit and nothing written",
              c6 == EXIT_SNAPSHOT_STALE and same6 and "SNAPSHOT STALE" in o6, FS)

        # ---------------------------------------------------------------- manifest meaning
        V = ("validate_manifest",)
        check("POS", "real manifest with its queue: no structural, semantic or corruption findings",
              not any(validate_manifest(m_cur, queue_bytes=q_cur)[c] for c in ("SCHEMA_INVALID", "SEMANTIC_INVALID", "BUNDLE_CORRUPT")), V)
        no_dec_pair = next(k for k in m_cur["queue"]["pair_keys"] if k != vp["key"])

        def sem(fn, cat="SEMANTIC_INVALID"):
            mm = copy.deepcopy(m_cur)
            fn(mm)
            return bool(validate_manifest(mm)[cat])

        def approve_without_decisions(mm):
            mm["decisions"].update(snapshot=[], records={}, counts={"current": 0, "stale": 0, "superseded": 0, "historical": 0})
            mm["import_approval"]["status"] = "APPROVED"
            for g in mm["import_approval"]["gates"].values():
                g["open"] = True

        def rendered_confirmation(mm):
            mm["queue"]["rendered"][no_dec_pair].update(resolution_status="OWNER_CONFIRMED", decision_status="CURRENT",
                                                        owner_disposition="CONFIRMED_SAME_LEGAL_OBJECT")

        def stale_as_current(mm):
            for x in mm["decisions"]["snapshot"]:
                if x["decision_id"] == "p2":
                    x["status"] = "STALE"

        def superseded_as_current(mm):
            for x in mm["decisions"]["snapshot"]:
                if x["decision_id"] == "p1":
                    x["status"] = "CURRENT"
            mm["decisions"]["counts"].update(current=2, superseded=0)
        for label, fn, cat in [("APPROVED with no decisions", approve_without_decisions, "SEMANTIC_INVALID"),
                               ("false decision counts", lambda mm: mm["decisions"]["counts"].update(current=83), "SEMANTIC_INVALID"),
                               ("rendered confirmation without a decision", rendered_confirmation, "SEMANTIC_INVALID"),
                               ("stale decision rendered as current", stale_as_current, "SEMANTIC_INVALID"),
                               ("superseded decision counted as current", superseded_as_current, "SEMANTIC_INVALID"),
                               ("G03 open while pairs are unresolved", lambda mm: mm["import_approval"]["gates"]["G03"].update(open=True), "SEMANTIC_INVALID"),
                               ("integrity PASS with a failed check", lambda mm: mm["integrity"]["checks"].update(I05=False), "SEMANTIC_INVALID"),
                               ("notes fingerprint mismatch", lambda mm: mm["notes"].update(snapshot_sha256="f" * 64), "SEMANTIC_INVALID"),
                               ("decision record digest mismatch", lambda mm: mm["decisions"]["records"].update(p2="f" * 64), "SEMANTIC_INVALID"),
                               ("empty live_inputs", lambda mm: mm.update(live_inputs={}), "SCHEMA_INVALID"),
                               ("invalid tool hash", lambda mm: mm["tool"].update(sha256="xyz"), "SCHEMA_INVALID"),
                               ("zero row count", lambda mm: mm["files"][REG].update(rows=0), "SCHEMA_INVALID"),
                               ("missing notes block", lambda mm: mm.pop("notes"), "SCHEMA_INVALID")]:
            check("NEG", f"manifest rejected ({cat}): {label}", sem(fn, cat), V)
        check("NEG", "manifest queue hash disagrees with the queue bytes -> BUNDLE_CORRUPT",
              bool(validate_manifest(m_cur, queue_bytes=q_cur + b"x")["BUNDLE_CORRUPT"]), V)
        m_a = json.loads(a_files[0])
        e_a = validate_manifest(m_a, T(pth), a_files[1])
        check("POS", "historical bundle A: internally valid, and correctly reported stale against today's notes and decisions",
              not e_a["SCHEMA_INVALID"] and not e_a["SEMANTIC_INVALID"] and not e_a["BUNDLE_CORRUPT"]
              and e_a["NOTES_CHANGED"] and e_a["DECISIONS_CHANGED"], V)

        # ---------------------------------------------------------------- decision snapshots are re-derived, never trusted
        tcur = T(pth)
        g_ok = gate_rec("g9")

        def forge(base_m, fn, t_=None, cat="SEMANTIC_INVALID"):
            mm = copy.deepcopy(base_m)
            fn(mm)
            return bool(validate_manifest(mm, t_)[cat])

        def status_only(mm):
            r = {"status": "APPROVED"}
            mm["decisions"]["snapshot"] = [{"decision_id": "g9", "kind": "gate", "subject": "cb_id_format",
                                            "status": "GATE_HEAD", "record": r}]
            mm["decisions"]["records"] = {"g9": sha256_bytes(canonical(r).encode("utf-8"))}
            mm["import_approval"]["gates"]["G04"] = {"open": True, "detail": "forged"}

        def snapshot_without_file(mm):
            mm["decisions"]["snapshot"] = [{"decision_id": "g9", "kind": "gate", "subject": "cb_id_format",
                                            "status": "GATE_HEAD", "record": g_ok}]
            mm["decisions"]["records"] = {"g9": sha256_bytes(canonical(g_ok).encode("utf-8"))}

        def invalid_record_matching_digest(mm):
            for x in mm["decisions"]["snapshot"]:
                if x["decision_id"] == "p1":
                    x["record"] = dict(x["record"], disposition="yes")
                    mm["decisions"]["records"]["p1"] = sha256_bytes(canonical(x["record"]).encode("utf-8"))

        def forged_head_claiming_current_file(mm):
            mm["decisions"]["snapshot"].append({"decision_id": "g9", "kind": "gate", "subject": "cb_id_format",
                                                "status": "GATE_HEAD", "record": g_ok})
            mm["decisions"]["records"]["g9"] = sha256_bytes(canonical(g_ok).encode("utf-8"))
            mm["import_approval"]["gates"]["G04"] = {"open": True, "detail": "forged"}
        for label, base_m, fn, t_, cat in [
                ("non-empty snapshot while decisions.present is false", m_a, snapshot_without_file, None, "SEMANTIC_INVALID"),
                ("decisions.present true with no sha256", m_cur, lambda mm: mm["decisions"].update(sha256=None), None, "SCHEMA_INVALID"),
                ("status-only GATE_HEAD record with a matching digest, G04 opened", m_a, status_only, None, "SEMANTIC_INVALID"),
                ("historical decision made invalid with a recomputed digest", m_d, invalid_record_matching_digest, None, "SEMANTIC_INVALID"),
                ("forged GATE_HEAD in a snapshot that claims the current decisions file", m_cur, forged_head_claiming_current_file, tcur, "SEMANTIC_INVALID"),
                ("G04 open without any gate decision", m_cur, lambda mm: mm["import_approval"]["gates"]["G04"].update(open=True), None, "SEMANTIC_INVALID")]:
            check("NEG", f"decision snapshot rejected: {label}", forge(base_m, fn, t_, cat), V)
        e_d = validate_manifest(m_d, tcur, files_of(pth, bid_d)[1])
        check("POS", "historical bundle with valid decisions stays internally valid while the current decisions differ",
              not e_d["SCHEMA_INVALID"] and not e_d["SEMANTIC_INVALID"] and bool(e_d["DECISIONS_CHANGED"]), V)

        # ---------------------------------------------------------------- lock and concurrency
        seen = {}

        def competing_freeze(p):
            seen.setdefault("freeze", refused(lambda: freeze(pth, ident, today, cached=base), Locked))
        HOOKS["after_prepare"] = competing_freeze
        write_notes(pth, [note(vp["key"], "process A")])
        try:
            _, bid_x, _ = freeze(pth, ident, today, cached=base)
        finally:
            HOOKS.clear()
        write_notes(pth, [note(vp["key"], "process B")])
        _, bid_y, _ = freeze(pth, ident, today, cached=base)
        hist = read_store(pth)["pointer"]["activated_bundles"]
        check("NEG", "freeze vs freeze from one starting pointer: the second is refused while the first holds the lock",
              seen.get("freeze") is True, X)
        check("POS", "serialized freezes: both bundles are in activation history, neither activation lost",
              bid_x in hist and bid_y in hist and hist[-1] == bid_y, X)
        HOOKS["after_prepare"] = lambda p: seen.setdefault("recover", refused(lambda: recover(pth, ident, today, cached=base), Locked))
        write_notes(pth, [note(vp["key"], "process C")])
        try:
            freeze(pth, ident, today, cached=base)
        finally:
            HOOKS.clear()
        check("NEG", "freeze vs recover: recover is refused while freeze holds the lock", seen.get("recover") is True, X)
        with transaction_lock(pth, "recover") as held:
            check("NEG", "recover vs recover: the second recover is refused", refused(lambda: recover(pth, ident, today, cached=base), Locked), X)
            check("NEG", "report refuses (exit 5) while a transaction holds the lock", quiet_code(pth) == EXIT_LOCKED, X)
        check("POS", "lock released after the holder finishes", not lock_held(pth), X)
        with transaction_lock(pth, "freeze") as held:
            staging = pth.audit_dir / "bundles" / f".staging-{'a' * 24}-{held}"
            staging.mkdir()
            check("NEG", "staging owned by an active transaction: recover refused, staging untouched",
                  refused(lambda: recover(pth, ident, today, cached=base), Locked) and staging.exists(), X)
        fired = {}

        def rewrite_pointer_once(key):
            def fn(p):
                if key not in fired:
                    fired[key] = True
                    c = p.audit_dir / "CURRENT.json"
                    c.write_bytes(json.dumps(json.loads(c.read_bytes())).encode())
            return fn
        ok_s, _ = recover(pth, ident, today, cached=base)
        HOOKS["after_prepare"] = rewrite_pointer_once("prep")
        write_notes(pth, [note(vp["key"], "restart")])
        try:
            _, _, how_r = freeze(pth, ident, today, cached=base)
        finally:
            HOOKS.clear()
        check("POS", "CURRENT changed after preparation: preparation restarts and completes cleanly",
              ok_s and fired.get("prep") and how_r == "activated" and read_store(pth)["state"] == "CLEAN", X)
        HOOKS["before_activate"] = rewrite_pointer_once("act")
        write_notes(pth, [note(vp["key"], "activation race")])
        try:
            raced = refused(lambda: freeze(pth, ident, today, cached=base))
        finally:
            HOOKS.clear()
        forged = cur(pth)
        s_r = read_store(pth)
        check("NEG", "CURRENT changed after publishing, before activation: refused, CURRENT not overwritten, bundle left unactivated",
              raced and cur(pth) == forged and len(s_r["orphans"]) == 1 and not lock_held(pth), X)
        orphan = s_r["orphans"][0].name
        ok_r, _ = recover(pth, ident, today, cached=base)
        check("POS", "recover activates that bundle (it is what a freeze would produce now)",
              ok_r and read_store(pth)["pointer"]["bundle_id"] == orphan, X)

        # ---------------------------------------------------------------- OS lock, in process
        (pth.audit_dir / ".lock.owner.json").write_text("{corrupt", encoding="utf-8")
        how_m = freeze(pth, ident, today, cached=base)[2]
        check("POS", "corrupt owner metadata neither blocks nor authorises anything; the next holder rewrites it",
              how_m in ("unchanged", "activated", "reactivated") and isinstance(last_holder(pth), dict), X)
        (pth.audit_dir / ".lock.owner.json").unlink()
        check("POS", "missing owner metadata neither blocks nor authorises anything",
              freeze(pth, ident, today, cached=base)[2] in ("unchanged", "activated", "reactivated") and not lock_held(pth), X)
        with transaction_lock(pth, "freeze"):
            check("NEG", "an independent handle cannot take a held lock", lock_held(pth), X)
        check("POS", "the lock is free again when the holder's block ends", not lock_held(pth), X)
        write_notes(pth, [note("CE-00134-BX|CB-1000002")])
        check("POS", "lock released after an ordinary refusal inside the transaction",
              refused(lambda: freeze(pth, ident, today, cached=base)) and not lock_held(pth), X)
        write_notes(pth, [note(vp["key"])])
        real_os_lock = M._os_lock
        M._os_lock = lambda fh: (_ for _ in ()).throw(OSError(5, "simulated I/O error"))
        try:
            try:
                freeze(pth, ident, today, cached=base)
                kind = None
            except Locked:
                kind = "Locked"
            except Refused:
                kind = "Refused"
        finally:
            M._os_lock = real_os_lock
        check("NEG", "a lock error that is not a conflict is a refusal, not a crash, a wait or a false Locked", kind == "Refused", X)

        # ---------------------------------------------------------------- transactions and inventory
        before = cur(pth)
        write_notes(pth, [note(vp["key"], "staging failure")])
        M._write_new = lambda path, data: (_ for _ in ()).throw(OSError("disk")) \
            if Path(path).parent.name.startswith(".staging-") and Path(path).name == "queue.csv" else real_write(path, data)
        try:
            crashed = refused(lambda: freeze(pth, ident, today, cached=base), OSError)
        finally:
            M._write_new = real_write
        check("NEG", "failure while staging: CURRENT untouched, lock released, INCOMPLETE, report exit 3, freeze refused",
              crashed and cur(pth) == before and not lock_held(pth) and read_store(pth)["state"] == "INCOMPLETE"
              and quiet_code(pth) == EXIT_TRANSACTION and refused(lambda: freeze(pth, ident, today, cached=base)), X)
        ok1, _ = recover(pth, ident, today, cached=base)
        n_abandoned = sum(1 for i in inventory(pth) if i["state"].startswith("abandoned"))
        ok2, _ = recover(pth, ident, today, cached=base)
        check("POS", "recover sets the staging aside; a second recover creates no further copies",
              ok1 and ok2 and sum(1 for i in inventory(pth) if i["state"].startswith("abandoned")) == n_abandoned, X)
        os.replace = lambda src, dst: (_ for _ in ()).throw(PermissionError("lock")) \
            if Path(dst).name == "CURRENT.json" else real_replace(src, dst)
        try:
            locked_out = refused(lambda: freeze(pth, ident, today, cached=base), PermissionError)
            rec_failed = refused(lambda: recover(pth, ident, today, cached=base), PermissionError)
        finally:
            os.replace = real_replace
        s_l = read_store(pth)
        check("NEG", "pointer replace blocked, then recovery blocked too: CURRENT intact, bundle intact, lock released",
              locked_out and rec_failed and cur(pth) == before and len(s_l["orphans"]) == 1 and not lock_held(pth), X)
        ok3, _ = recover(pth, ident, today, cached=base)
        check("POS", "recover then activates exactly that bundle", ok3 and read_store(pth)["pointer"]["bundle_id"] == s_l["orphans"][0].name, X)
        for n_ in range(2):
            leftover = pth.audit_dir / "bundles" / f".staging-{'b' * 24}-freeze-99999999.{'c' * 12}"
            leftover.mkdir()
            (leftover / "manifest.json").write_bytes(b"identical partial content")
            check("NEG", f"interrupted leftover #{n_ + 1} is detected as INCOMPLETE", read_store(pth)["state"] == "INCOMPLETE", X)
            recover(pth, ident, today, cached=base)
        states = [i["state"] for i in inventory(pth)]
        abandoned = [i for i in inventory(pth) if i["state"].startswith("abandoned")]
        check("POS", "identical leftovers share a digest: the second is marked a duplicate, with reason and transaction",
              "abandoned-duplicate" in states and all(i["reason"] for i in abandoned)
              and any(i["transaction_id"] == f"freeze-99999999.{'c' * 12}" for i in abandoned), X)
        check("POS", "inventory reports active and historical bundles and abandoned remnants",
              "active" in states and "historical" in states and read_store(pth)["state"] == "CLEAN", X)
        good = cur(pth)
        (pth.audit_dir / "CURRENT.json").write_bytes(b"not json")
        check("NEG", "invalid pointer: freeze and recover refuse and leave it as found",
              refused(lambda: freeze(pth, ident, today, cached=base)) and refused(lambda: recover(pth, ident, today, cached=base))
              and cur(pth) == b"not json", X)
        (pth.audit_dir / "CURRENT.json").write_bytes(good)

    with tempfile.TemporaryDirectory() as d:
        pth2 = paths_in(Path(d))
        os.replace = lambda src, dst: (_ for _ in ()).throw(PermissionError("lock")) \
            if Path(dst).name == "CURRENT.json" else real_replace(src, dst)
        try:
            first_failed = refused(lambda: freeze(pth2, ident, today, cached=base), PermissionError)
        finally:
            os.replace = real_replace
        s_f = read_store(pth2)
        check("NEG", "first freeze fails at the commit point: no pointer, one unactivated bundle",
              first_failed and s_f["pointer_state"] == "ABSENT" and len(s_f["orphans"]) == 1, X)
        okf, _ = recover(pth2, ident, today, cached=base)
        check("POS", "recover activates the first bundle", okf and read_store(pth2)["pointer_state"] == "VALID", X)

    # ---------------------------------------------------------------- historical v2 bundle
    real_bundles = PROD.audit_dir / "bundles"
    v2 = next((p for p in sorted(real_bundles.iterdir()) if (p / "manifest.json").exists()
               and json.loads((p / "manifest.json").read_text(encoding="utf-8")).get("schema") == MANIFEST_SCHEMA_V2), None) \
        if real_bundles.exists() else None
    check("POS", "a historical v2 bundle exists to migrate from", v2 is not None, ("read_store",))
    if v2 is not None:
        vm, vq = (v2 / "manifest.json").read_bytes(), (v2 / "queue.csv").read_bytes()

        def plant_v2(pth, mb, qb):
            bid = sha256_bytes(mb + b"\0" + qb)[:24]
            (pth.audit_dir / "bundles" / bid).mkdir(parents=True)
            (pth.audit_dir / "bundles" / bid / "manifest.json").write_bytes(mb)
            (pth.audit_dir / "bundles" / bid / "queue.csv").write_bytes(qb)
            m = json.loads(mb)
            (pth.audit_dir / "CURRENT.json").write_text(json.dumps(
                {"schema": POINTER_SCHEMA, "bundle_id": bid, "manifest_sha256": sha256_bytes(mb),
                 "queue_generated_sha256": m["queue"]["sha256"], "activated_bundles": [bid]}), encoding="utf-8")
            return bid
        with tempfile.TemporaryDirectory() as d:
            pth3 = paths_in(Path(d))
            old = plant_v2(pth3, vm, vq)
            _, new, _ = freeze(pth3, ident, today, cached=base)
            s3 = read_store(pth3)
            check("POS", "v2 current bundle migrates: v3 activated, v2 kept in history, nothing corrupt",
                  s3["state"] == "CLEAN" and s3["pointer"]["activated_bundles"] == [old, new]
                  and s3["manifest"]["schema"] == MANIFEST_SCHEMA, ("freeze", "read_store"))
        with tempfile.TemporaryDirectory() as d:
            pth4 = paths_in(Path(d))
            rows = dicts(parse_csv(vq))
            rows[0]["YOUR_NOTES"] = "typed inside a bundle"
            buf = io.StringIO(newline="")
            w = csv.DictWriter(buf, fieldnames=QUEUE_COLUMNS_V2, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            qb2 = buf.getvalue().encode("utf-8")
            mv = json.loads(vm)
            mv["queue"]["sha256"] = sha256_bytes(qb2)
            plant_v2(pth4, (json.dumps(mv, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"), qb2)
            check("NEG", "v2 bundle holding notes typed inside it -> freeze refused until they are moved to the notes file",
                  refused(lambda: freeze(pth4, ident, today, cached=base)), ("freeze", "prepare"))

    # ---------------------------------------------------------------- every consequential input is rechecked at activation
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        pthc = replace(paths_in(dd), ledger=dd / "ledger.csv", policy_code=dd / "cedar_domain.py")
        pthc.ledger.write_bytes(PROD.ledger.read_bytes())
        pthc.policy_code.write_bytes(PROD.policy_code.read_bytes())
        write_notes(pthc, [])
        freeze(pthc, ident, today, cached=base)
        check("POS", "store on copied ledger and policy code: first freeze activated from verified inputs",
              read_store(pthc)["state"] == "CLEAN", S)
        write_notes(pthc, [note(vp["key"], "before preparation")])
        _, _, how_b = freeze(pthc, ident, today, cached=base)
        check("POS", "input changed before preparation: prepared and activated with the new input",
              how_b == "activated" and qrows(pthc)[vp["key"]]["owner_note_snapshot"] == "before preparation", X)
        fired = {}

        def once_after_prepare(p):
            if not fired:
                fired["x"] = True
                write_notes(pthc, [note(vp["key"], "after preparation")])
        HOOKS["after_prepare"] = once_after_prepare
        try:
            freeze(pthc, ident, today, cached=base)
        finally:
            HOOKS.clear()
        check("POS", "input changed after preparation, before publication: preparation restarts; the new input is what activates",
              bool(fired) and qrows(pthc)[vp["key"]]["owner_note_snapshot"] == "after preparation", X)
        for label, key, mutate, restore in [
                ("notes only", "notes", lambda: write_notes(pthc, [note(vp["key"], "raced")]), lambda: None),
                ("decisions only", "decisions", lambda: pthc.decisions.write_bytes(json.dumps(
                    {"schema": DECISIONS_SCHEMA, "gates": {}, "proposed_equivalence_pairs": []}).encode()),
                 lambda: pthc.decisions.unlink()),
                ("the ledger", "ledger", lambda: pthc.ledger.write_bytes(PROD.ledger.read_bytes() + b"\n"),
                 lambda: pthc.ledger.write_bytes(PROD.ledger.read_bytes())),
                ("policy code", "policy_code", lambda: pthc.policy_code.write_bytes(PROD.policy_code.read_bytes() + b"\n# changed\n"),
                 lambda: pthc.policy_code.write_bytes(PROD.policy_code.read_bytes()))]:
            write_notes(pthc, [note(vp["key"], f"iteration {label}")])
            notes_before, cur_before = pthc.notes.read_bytes(), cur(pthc)
            HOOKS["before_activate"] = lambda p, m=mutate: m()
            try:
                try:
                    freeze(pthc, ident, today, cached=base)
                    msg = ""
                except Refused as e:
                    msg = str(e)
            finally:
                HOOKS.clear()
            s_x = read_store(pthc)
            check("NEG", f"{label} changed after publication, before activation: nothing activated, '{key}' named, bundle kept",
                  key in msg and cur(pthc) == cur_before and len(s_x["orphans"]) == 1 and not lock_held(pthc), X, msg[:90])
            restore()
            pthc.notes.write_bytes(notes_before)
            ok_x, _ = recover(pthc, ident, today, cached=base)
            check("POS", f"{label} restored: recover verifies inputs inside the lock and activates the bundle they reproduce",
                  ok_x and read_store(pthc)["pointer"]["bundle_id"] == s_x["orphans"][0].name, X)
        write_notes(pthc, [note(vp["key"], "recover race")])
        notes_before = pthc.notes.read_bytes()
        HOOKS["before_activate"] = lambda p: (_ for _ in ()).throw(Refused("simulated stop before activation"))
        try:
            refused(lambda: freeze(pthc, ident, today, cached=base))
        finally:
            HOOKS.clear()
        HOOKS["recover_before_activate"] = lambda p: write_notes(pthc, [note(vp["key"], "changed during recover")])
        try:
            try:
                recover(pthc, ident, today, cached=base)
                rmsg = ""
            except Refused as e:
                rmsg = str(e)
        finally:
            HOOKS.clear()
        s_rr = read_store(pthc)
        check("NEG", "input changed during recover: nothing activated, 'notes' named, bundle kept, lock released",
              "notes" in rmsg and len(s_rr["orphans"]) == 1 and not lock_held(pthc), X, rmsg[:90])
        pthc.notes.write_bytes(notes_before)
        calls = {"n": 0}
        real_load = M.load

        def counting_load(p):
            calls["n"] += 1
            return real_load(p)
        M.load = counting_load
        try:
            ok_rr, _ = recover(pthc, ident, today, cached=dict(base, live_sha=dict(base["live_sha"], ledger="0" * 64)))
        finally:
            M.load = real_load
        check("POS", "recover given a stale cache reloads inputs inside the lock and activates only what they reproduce",
              ok_rr and calls["n"] == 1 and read_store(pthc)["state"] == "CLEAN", X)
        check("POS", "the input snapshot covers every consequential input and CURRENT",
              set(input_snapshot(pthc)) == set(SNAPSHOT_KEYS) | {"tool", "CURRENT"}, ("input_snapshot",))

    # ---------------------------------------------------------------- independent processes on the real filesystem
    CHILD = r"""
import importlib.util, json, os, sys, time
from dataclasses import replace
from pathlib import Path
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("r7audit", sys.argv[1])
M = importlib.util.module_from_spec(spec)
sys.modules["r7audit"] = M
spec.loader.exec_module(M)
d, action = Path(sys.argv[2]), sys.argv[3]
paths = replace(M.PROD, decisions=d / "decisions.json", notes=d / "notes.json", audit_dir=d / "audit")
try:
    if action == "hold":
        with M.transaction_lock(paths, "freeze"):
            (d / "held").write_text("1")
            while not (d / "release").exists():
                time.sleep(0.05)
        sys.exit(0)
    if action == "freeze-die-before-activate":
        M.HOOKS["before_activate"] = lambda p: os._exit(9)
    if action.startswith("freeze"):
        ev, bid, how = M.freeze(paths)
        print(json.dumps({"bid": bid, "how": how}))
        sys.exit(0)
    if action == "recover":
        ok, actions = M.recover(paths)
        print(json.dumps({"ok": ok, "actions": actions}))
        sys.exit(0 if ok else 1)
    if action == "report":
        sys.exit(M.report(paths))
except M.Locked:
    sys.exit(5)
except M.Refused as e:
    print("REFUSED", e)
    sys.exit(1)
"""
    SP = ("transaction_lock", "lock_held", "freeze", "recover", "read_store")
    prod_file = str(Path(M.__file__).resolve())

    def cmd(dd, action):
        return [sys.executable, "-B", "-c", CHILD, prod_file, str(dd), action]

    def run(dd, action):
        return subprocess.run(cmd(dd, action), capture_output=True, text=True, timeout=900)

    def start(dd, action):
        return subprocess.Popen(cmd(dd, action), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def wait_for_lock(pth, seconds=120):
        """The flag file says a holder started; only this says the lock is actually held."""
        end = time.time() + seconds
        while time.time() < end:
            if lock_held(pth):
                return True
            time.sleep(0.05)
        return False

    def wait_for(p, seconds=120):
        end = time.time() + seconds
        while time.time() < end:
            if p.exists():
                return True
            time.sleep(0.1)
        return False
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        psp = paths_in(dd)
        write_notes(psp, [])
        first = run(dd, "freeze")
        check("POS", "subprocess: a freeze in an independent process activates", first.returncode == 0
              and read_store(psp)["state"] == "CLEAN", SP, first.stdout.strip()[-80:])
        holder = start(dd, "hold")
        held = wait_for(dd / "held")
        fb, rb = run(dd, "freeze").returncode, run(dd, "recover").returncode
        check("NEG", "subprocess: while another process holds the lock, freeze and recover in other processes exit 5",
              held and fb == 5 and rb == 5 and lock_held(psp), SP, f"{fb}/{rb}")
        racers = [start(dd, "freeze"), start(dd, "recover")]
        codes = [p.wait(timeout=900) for p in racers]
        check("NEG", "subprocess: simultaneous freeze and recover against the held lock both refuse; the holder keeps it",
              codes == [5, 5] and lock_held(psp) and holder.poll() is None, SP, str(codes))
        (dd / "release").write_text("1")
        holder.wait(timeout=120)
        check("POS", "subprocess: the holder releases the lock by exiting", holder.returncode == 0 and not lock_held(psp), SP)
        (dd / "held").unlink()
        (dd / "release").unlink()
        victim = start(dd, "hold")
        wait_for(dd / "held")
        victim.kill()
        victim.wait(timeout=60)
        (dd / "held").unlink(missing_ok=True)  # killed mid-transaction: it never cleaned up its own flag
        after_kill = run(dd, "freeze")
        check("POS", "subprocess: a holder killed mid-transaction leaves no stale lock; the next freeze proceeds",
              not lock_held(psp) and after_kill.returncode == 0, SP, after_kill.stdout.strip()[-80:])
        ptr_before = cur(psp)
        write_notes(psp, [note(vp["key"], "published then killed")])
        died = run(dd, "freeze-die-before-activate")
        s_k = read_store(psp)
        check("NEG", "subprocess: killed after publication, before activation: CURRENT intact, bundle orphaned, lock released",
              died.returncode == 9 and cur(psp) == ptr_before and s_k["pointer_state"] == "VALID"
              and len(s_k["orphans"]) == 1 and not lock_held(psp), SP, str(died.returncode))
        orphan_k = s_k["orphans"][0].name if s_k["orphans"] else ""
        rec = [start(dd, "recover"), start(dd, "recover")]
        rc = sorted(p.wait(timeout=900) for p in rec)
        s_rk = read_store(psp)
        hist_k = s_rk["pointer"]["activated_bundles"]
        check("POS", "subprocess: two recovers racing: the orphan is activated once, the other refuses or finds nothing",
              rc in ([0, 0], [0, 5]) and s_rk["state"] == "CLEAN" and s_rk["pointer"]["bundle_id"] == orphan_k
              and len(set(hist_k)) == len(hist_k), SP, str(rc))
        rep_locked = run(dd, "report")
        check("POS", "subprocess: an unlocked report in its own process exits 10 (integrity valid, import not approved)",
              rep_locked.returncode == EXIT_NOT_APPROVED, SP, str(rep_locked.returncode))
        (dd / "held").unlink(missing_ok=True)
        holder2 = start(dd, "hold")
        held2 = wait_for(dd / "held") and wait_for_lock(psp)
        rep_busy = run(dd, "report")
        (dd / "release").write_text("1")
        holder2.wait(timeout=120)
        (dd / "held").unlink()
        (dd / "release").unlink()
        check("NEG", "subprocess: report while another process holds the lock exits 5",
              held2 and rep_busy.returncode == EXIT_LOCKED, SP, str(rep_busy.returncode))
        write_notes(psp, [note(vp["key"], "report and freeze racing")])
        pair = [start(dd, "report"), start(dd, "freeze")]
        pair_codes = [p.wait(timeout=900) for p in pair]
        s_pair = read_store(psp)
        check("POS", "subprocess: report and freeze racing: each either owns the lock or refuses; no mixed snapshot, store CLEAN",
              pair_codes[0] in (EXIT_NOT_APPROVED, EXIT_LOCKED) and pair_codes[1] in (0, EXIT_LOCKED)
              and s_pair["state"] == "CLEAN" and len(set(s_pair["pointer"]["activated_bundles"])) == len(s_pair["pointer"]["activated_bundles"]),
              SP, str(pair_codes))
        write_notes(psp, [note(vp["key"], "two freezes")])
        fz = [start(dd, "freeze"), start(dd, "freeze")]
        fc = sorted(p.wait(timeout=900) for p in fz)
        s_fz = read_store(psp)
        hist_f = s_fz["pointer"]["activated_bundles"]
        check("POS", "subprocess: two freezes racing from one pointer: one activation, the other refused or unchanged",
              fc in ([0, 0], [0, 5]) and s_fz["state"] == "CLEAN" and len(set(hist_f)) == len(hist_f)
              and qrows(psp)[vp["key"]]["owner_note_snapshot"] == "two freezes", SP, str(fc))

    # ---------------------------------------------------------------- git must not convert hashed bytes
    GA = ("gitattributes",)
    live = PROD.audit_dir
    ptr = json.loads((live / "CURRENT.json").read_text(encoding="utf-8"))
    probe = ["docs/imports/r7_audit/CURRENT.json", f"docs/imports/r7_audit/bundles/{ptr['bundle_id']}/manifest.json",
             f"docs/imports/r7_audit/bundles/{ptr['bundle_id']}/queue.csv", "docs/imports/R7_OWNER_NOTES.json"]
    attrs = subprocess.run(["git", "-C", str(CEDAR), "check-attr", "text", "--"] + probe, capture_output=True, text=True).stdout
    check("POS", "git check-attr: CURRENT.json, bundle manifests and bundle queues are -text",
          all(f"{p}: text: unset" in attrs for p in probe[:3]), GA, attrs.strip().replace("\n", " | ")[:200])
    check("POS", "git check-attr: files outside docs/imports/r7_audit keep normal handling",
          f"{probe[3]}: text: unspecified" in attrs, GA)

    def git(cwd, autocrlf, *args):
        return subprocess.run(["git", "-c", f"core.autocrlf={autocrlf}", "-c", "core.safecrlf=false", *args],
                              cwd=cwd, capture_output=True, text=True)
    for with_attrs, autocrlf in ((True, "true"), (True, "input"), (False, "true")):
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            git(dd, autocrlf, "init", "-q")
            target = dd / "docs/imports/r7_audit"
            names = [target / "CURRENT.json"]
            for bid in ptr["activated_bundles"]:
                (target / "bundles" / bid).mkdir(parents=True)
                for fname in ("manifest.json", "queue.csv"):
                    names.append(target / "bundles" / bid / fname)
            for pth_ in names:
                pth_.parent.mkdir(parents=True, exist_ok=True)
                pth_.write_bytes((live / pth_.relative_to(target)).read_bytes())
            if with_attrs:
                (dd / ".gitattributes").write_bytes((CEDAR / ".gitattributes").read_bytes())
            git(dd, autocrlf, "add", "-A")
            for pth_ in names:
                pth_.unlink()
            git(dd, autocrlf, "checkout-index", "-a", "-f")
            ids_ok = all(sha256_bytes((target / "bundles" / bid / "manifest.json").read_bytes() + b"\0"
                                      + (target / "bundles" / bid / "queue.csv").read_bytes())[:24] == bid
                         for bid in ptr["activated_bundles"])
            cur_ok = (target / "CURRENT.json").read_bytes() == (live / "CURRENT.json").read_bytes()
            if with_attrs:
                check("POS", f"index round trip with core.autocrlf={autocrlf} and the attributes: bundle ids and CURRENT byte-identical",
                      ids_ok and cur_ok, GA)
            else:
                check("NEG", "control without the attributes: core.autocrlf=true checkout changes the bytes and every bundle id",
                      not ids_ok, GA)

    # ---------------------------------------------------------------- arguments
    A = ("main",)
    for argv in ([], ["freeze"], ["recover"]):
        check("POS", f"arguments {argv} accepted", main(argv, _probe=True) == 0, A)
    for argv in (["--apply"], ["selftest"], ["selftest", "freeze"], ["freeze", "--force"], ["recover", "x"],
                 ["unlock", "freeze-1.abcdefabcdef"]):
        check("NEG", f"arguments {argv} rejected with exit 2", main(argv, _probe=True) == 2, A)

    pos = sum(1 for k, _, _ in results if k == "POS")
    neg = sum(1 for k, _, _ in results if k == "NEG")
    failed = [label for _, label, ok in results if not ok]
    print(f"\n  assertions executed: {len(results)}  (positive controls {pos}, negative fixtures {neg})  failed: {len(failed)}")
    print(f"  production functions exercised: {', '.join(sorted(used))}")
    if failed:
        print(f"SELFTEST FAIL: {failed}")
        return 1
    print("SELFTEST PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
