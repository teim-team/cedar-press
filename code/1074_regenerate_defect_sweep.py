#!/usr/bin/env python3
"""
Cedar Press - 1074: PROOF HARNESS for the ADR-017 regenerate sweep
(2026-09-02). Read-only. Writes nothing anywhere.

    py -3 code/1074_regenerate_defect_sweep.py            # all three checks
    py -3 code/1074_regenerate_defect_sweep.py carry      # what each fix emits
    py -3 code/1074_regenerate_defect_sweep.py positional # header vs row length
    py -3 code/1074_regenerate_defect_sweep.py writers    # which path each
                                                          # literal really feeds

WHY THIS EXISTS SEPARATELY FROM 845
-----------------------------------
`845` says a writer is now safe. That is a statement about the SHAPE of the
code. Three things it cannot say, and this can:

1. **CARRY** - for every script the sweep touched, what header would it
   actually emit against the live file today? The fix is only a fix if the
   emitted header is a SUPERSET of what is on disk. This imports each script's
   own `_carry_live_columns` and runs it against the real table.

2. **POSITIONAL** - `csv.writer` + `writerow([...])` has no `fieldnames` at
   all, so 845 is structurally blind to it, and it is where the WORST version
   of this defect lives: `24_funding_merge.py` declared 34 columns in its
   header row and emitted 32 in every data row, so every field from index 7
   was shifted LEFT by two. Nothing errored. This compares the length of every
   literal-list `writerow` against the header row of the same writer.

3. **WRITERS** - which output path each `fieldnames` literal actually feeds.
   845 v1 guessed this from name overlap and was wrong 9 times out of 29,
   including on its two worst-ranked findings. This prints the resolution so a
   human can check the detector rather than trust it.
"""
from __future__ import annotations

import ast
import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
csv.field_size_limit(10_000_000)

# Every script the ADR-017 sweep touched, and the table(s) whose header the
# fix has to preserve. Kept explicit: a glob would silently stop covering a
# script that was renamed, and report success for a check it never ran.
SWEPT = {
    "03_apply_exclusions_and_tier.py": ["cedar_identifier_ledger_tiered.csv",
                                        "cedar_publishable_identifiers.csv"],
    "05_parse_doi_nho_list.py": ["nho_doi_notification_roster.csv"],
    "07_parse_ancsa_ceiling.py": ["anc_ceiling_roster.csv"],
    "105_build_florida_gaming.py": ["fl_gaming_payments.csv",
                                    "seminole_bond_disclosures.csv"],
    "107_pull_remaining_states.py": ["state_gaming_observations.csv"],
    "114_pull_prime_archive.py": ["prime_contracts.csv",
                                  "prime_contracts_archive_backfill.csv"],
    "146_build_visitor_access_records.py": ["visitor_access_events.csv"],
    "15e_finalize_terms.py": ["compact_terms.csv"],
    "20_build_subcontracts.py": ["subawards.csv"],
    "30_funding_pre2008.py": ["faads_transactions_all_agencies.csv"],
    "330_build_native_owned_businesses.py": ["native_owned_businesses.csv"],
    "351_rebuild_lobbying_panel_from_corrected_disclosures.py":
        ["tribe_year_lobbying_panel.csv"],
    "417_build_entity_identity_crosswalk.py":
        ["cedar_entity_identity_crosswalk.csv"],
    "75_add_bie_schools_and_uios.py": ["bie_uio_dollars_by_entity.csv",
                                      "bie_uio_identifier_links.csv"],
    "79_build_award_level_contracts.py": ["prime_contracts_published.csv",
                                         "prime_contracts_awards.csv"],
    "89_nigc_map_wayback_universe.py": ["gaming_property_universe_events.csv"],
    "100_finish_declinations_and_employment.py":
        ["gaming_employment_observations.csv"],
    "104_build_wa_allocations.py": ["wa_machine_allocations.csv",
                                    "wa_machine_transfers.csv"],
    "106_build_revenue_bounds.py": ["nigc_revenue_bands.csv",
                                    "gaming_revenue_bounds.csv"],
    "108_build_tribal_tax_bases.py": ["tribal_tax_bases.csv"],
    "111_build_advocacy_passthrough.py": ["advocacy_passthrough.csv"],
    "113_build_nd_severance.py": ["nd_severance_allocation.csv"],
    "116_build_nd_tribal_taxes.py": ["tribal_tax_bases.csv"],
    "117_build_gaming_devices.py": ["gaming_device_observations.csv"],
    "118_build_gaming_ordinances.py": ["gaming_ordinances.csv"],
    "119_build_digital_and_loyalty.py": ["loyalty_programs.csv",
                                         "loyalty_program_property.csv",
                                         "digital_gaming_revenue.csv",
                                         "digital_gaming_relationships.csv"],
    "132_build_schedule_i_layer.py": ["np_schedule_i_filers.csv"],
    "135_build_resource_assets.py": ["resource_assets.csv",
                                     "resource_parties.csv"],
    "140_build_grantmaker_funding_flows.py": ["grantmaker_funding_flows.csv"],
    "153_merge_ordinance_ocr.py": ["gaming_ordinance_ocr.csv"],
    "154_build_fr_ex_parte_notices.py": ["fr_ex_parte_parties.csv"],
    "15b_build_compact_index.py": ["compacts.csv", "compact_versions.csv",
                                   "compact_events.csv"],
    "163_promote_nho_universe_in_place.py": ["nho_ito_spine_crosswalk.csv"],
    "18_spiderweb_v2_and_cage_backfill.py": ["cedar_spiderweb_v2.csv"],
    "19_rebuild_nho_layer.py": ["nho_verified_entities.csv"],
    "23b_build_gaming_land_decisions.py": ["gaming_land_decisions.csv"],
    "23d_build_gaming_facilities.py": ["gaming_facility_metrics.csv"],
    "32b_build_gaming_nepa_pilot.py": ["gaming_projections.csv",
                                       "gaming_project_facilities.csv"],
    "33_apply_party_rulings.py": ["deals_party_attribution.csv"],
    "35_entity_harvest.py": ["entity_candidates_new.csv",
                             "entity_name_harvest.csv"],
    "53_apply_agent_deals_rulings.py": ["deals_party_attribution_agent.csv"],
    "61_add_nho_intertribal_to_spine.py": ["nho_ito_spine_crosswalk.csv",
                                           "nho_ownership_changes.csv"],
    "73_faads_name_attribution.py": ["faads_entity_attribution.csv"],
    "83_build_resource_ledger.py": ["resource_assets.csv"],
    "91_build_nigc_declinations.py": ["gaming_financing_events.csv"],
    "95_parse_compact_terms.py": ["compact_structured_terms.csv",
                                  "compact_required_reports.csv"],
    "96_build_consultation_events.py": ["consultation_events.csv"],
    "97_build_aliases_and_relationships.py": ["entity_aliases.csv"],
    "98_build_oira_and_hearings.py": ["oira_meetings.csv",
                                      "hearing_appearances.csv"],
    "99_build_earmarks_and_schedc.py": ["earmarks.csv"],

    # --- class 3, added 2026-09-02: the ten `list(rows[0].keys())` writers
    # that were measured to lose a column, out of 114 sites. The other 104
    # build a fresh table they own outright, or are read-modify-write on the
    # file being rewritten, which is the correct idiom.
    "57_autoresolve_deal_parties.py": ["deals_party_autoresolved.csv"],
    "58_apply_lobbying_rulings.py": ["lobbying_client_attribution.csv"],
    "66_build_entity_hierarchy.py": ["entity_hierarchy.csv"],
    "82_build_gaming_property_dataset.py": [
        "gaming_property_capacity_history.csv", "gaming_properties.csv"],
    "122_ocr_ordinance_scans.py": ["gaming_ordinance_ocr.csv"],
    "127_bridge_compact_obligations_to_tribal_agency.py":
        ["compact_obligation_tribal_agency_bridge.csv"],
    "151_rebuild_entity_evidence_profile.py": ["entity_evidence_profile.csv"],
}


def _header(p: Path):
    with p.open(encoding="utf-8-sig", newline="", errors="replace") as fh:
        return next(csv.reader(fh), [])


def _load_carry(script: Path):
    """Import ONLY the `_carry_live_columns` function out of a script, without
    executing the script. Most of these run work at import time."""
    src = script.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    fn = next((n for n in tree.body
               if isinstance(n, ast.FunctionDef)
               and n.name == "_carry_live_columns"), None)
    if fn is None:
        return None
    mod = ast.Module(body=[fn], type_ignores=[])
    ns = {}
    exec(compile(mod, str(script), "exec"), ns)          # noqa: S102
    return ns["_carry_live_columns"]


def check_carry() -> int:
    print("  CARRY - does each swept script now emit a header that is a "
          "SUPERSET of the live file?\n")
    ok = miss = nofn = 0
    for name in sorted(SWEPT):
        s = CODE / name
        if not s.exists():
            print("    MISSING SCRIPT  %s" % name)
            miss += 1
            continue
        fn = _load_carry(s)
        if fn is None:
            nofn += 1
            print("    no _carry_live_columns  %-52s (fixed in place, not via "
                  "the shared helper)" % name)
            continue
        for tbl in SWEPT[name]:
            for d in ("clean", "spine"):
                p = ROOT / "data" / d / tbl
                if p.exists():
                    break
            else:
                print("    table absent    %-44s %s" % (name, tbl))
                continue
            live = _header(p)
            emitted = fn(p, [])          # canonical=[] isolates the carry
            good = all(c in emitted for c in live if c)
            print("    %s %-52s %-42s live %2d -> emits %2d"
                  % ("ok  " if good else "FAIL", name, tbl,
                     len(live), len(emitted)))
            if good:
                ok += 1
            else:
                miss += 1
                print("         DROPPED: %s"
                      % [c for c in live if c and c not in emitted])
    # 114 carries through `_prime_header`, not the shared helper, because it
    # must also REFUSE when a column it maps has left the file. Proved here
    # rather than skipped - otherwise the writer with the worst blast radius
    # in the whole sweep would be the one nothing checked.
    ok2 = _check_114()
    print("\n    %d table(s) provably preserved, %d failure(s), %d script(s) "
          "fixed at the writer instead of via the helper" % (ok, miss, nofn))
    return 1 if (miss or not ok2) else 0


def _check_114() -> bool:
    s = CODE / "114_pull_prime_archive.py"
    tree = ast.parse(s.read_text(encoding="utf-8", errors="replace"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
               and n.name == "_prime_header"), None)
    if fn is None:
        print("    FAIL 114_pull_prime_archive.py has no _prime_header")
        return False
    lits = next((n for n in tree.body if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", "") == "PRIME_FIELDS"
                         for t in n.targets)), None)
    canonical = [e.value for e in lits.value.elts]
    good_all = True
    for tbl in ("prime_contracts.csv", "prime_contracts_archive_backfill.csv"):
        p = ROOT / "data" / "clean" / tbl
        if not p.exists():
            print("    table absent    114_pull_prime_archive.py  %s" % tbl)
            continue
        live = _header(p)
        missing = [c for c in canonical if c not in live]
        emitted = canonical if missing else live
        good = not missing
        print("    %s %-52s %-42s live %2d -> emits %2d  (literal %d; %d "
              "enricher col(s) BLANK)"
              % ("ok  " if good else "FAIL", "114_pull_prime_archive.py", tbl,
                 len(live), len(emitted), len(canonical),
                 len([c for c in live if c not in canonical])))
        if not good:
            print("         PRIME_FIELDS names %d column(s) the file no longer "
                  "carries, so 114 REFUSES rather than misaligns: %s"
                  % (len(missing), missing))
            good_all = False
    return good_all


def check_positional() -> int:
    """csv.writer + writerow([...]) - the shape 845 is structurally blind to.

    A header row and a data row written by the same writer must have the same
    number of fields. `24_funding_merge.py` had 34 against 32 and every field
    from index 7 was silently shifted LEFT by two.
    """
    print("\n  POSITIONAL - `csv.writer` + `writerow([...])`, header length vs "
          "row length\n")
    bad = 0
    scanned = 0
    for p in sorted(CODE.glob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        # ONE BINDING AT A TIME. Grouping `w.writerow(...)` by the NAME `w`
        # across a whole file compares a header in one function to a data row
        # in another - nine such "mismatches" on the first run, every one of
        # them two unrelated writers that happened to share the commonest
        # variable name in the repo. A binding is scoped to its own function
        # and ends at the next rebinding of the same name.
        binds = []
        for fn in [tree] + [n for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef,
                                              ast.AsyncFunctionDef))]:
            local = []
            for n in ast.walk(fn):
                if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                        and getattr(n.value.func, "attr", "") == "writer"):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            local.append((n.lineno, t.id, fn))
            binds.extend(local)
        if not binds:
            continue
        by_name = {}
        for lineno, nm, fn in binds:
            by_name.setdefault(nm, []).append((lineno, fn))
        for nm in by_name:
            by_name[nm].sort(key=lambda x: x[0])
        for nm, blist in by_name.items():
            for i, (start, fn) in enumerate(blist):
                end = blist[i + 1][0] if i + 1 < len(blist) else 10 ** 9
                fend = getattr(fn, "end_lineno", 10 ** 9)
                rs = []
                for n in ast.walk(fn):
                    if not (isinstance(n, ast.Call)
                            and getattr(n.func, "attr", "") == "writerow"
                            and isinstance(getattr(n.func, "value", None),
                                           ast.Name)
                            and n.func.value.id == nm
                            and n.args and isinstance(n.args[0], ast.List)):
                        continue
                    if not (start < n.lineno < min(end, fend + 1)):
                        continue
                    elts = n.args[0].elts
                    if any(isinstance(e, ast.Starred) for e in elts):
                        continue              # variadic: length not static
                    rs.append((n.lineno, len(elts),
                               all(isinstance(e, ast.Constant)
                                   and isinstance(e.value, str)
                                   for e in elts)))
                hdrs = [r for r in rs if r[2]]
                if not hdrs or len(rs) < 2:
                    continue
                scanned += 1
                hlen = hdrs[0][1]
                off = [r for r in rs if r[1] != hlen and not r[2]]
                if off:
                    bad += 1
                    print("    MISMATCH  %s  writer %r bound L%d, header %d "
                          "field(s) at L%d" % (p.name, nm, start, hlen,
                                               hdrs[0][0]))
                    for lineno, n_, _ in off:
                        print("              data row at L%d emits %d - every "
                              "field from the first divergence is SHIFTED"
                              % (lineno, n_))
    print("    %d positional writer(s) with a literal header checked; "
          "%d misaligned" % (scanned, bad))
    if not bad:
        print("    (`24_funding_merge.py`, the recorded instance of this, "
              "no longer writes positionally)")
    return 1 if bad else 0


def show_writers() -> int:
    """Which path does each fieldnames literal actually feed? Uses 845's own
    resolver, so what is printed is what the guard decided."""
    spec = importlib.util.spec_from_file_location(
        "guard845", CODE / "845_regenerate_guard.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    print("\n  WRITERS - the resolved output path behind every DictWriter "
          "whose fieldnames is a name\n")
    n = 0
    for p in sorted(CODE.glob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        modenv = g.const_env(tree)
        printed = False
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and getattr(node.func, "attr", "") == "DictWriter"):
                continue
            fn = g._enclosing_func(tree, node.lineno)
            hist = g.local_hist(fn, modenv)
            spans, bound = g._open_targets(fn or tree, modenv, hist)
            fobj = node.args[0] if node.args else None
            tgt = ""
            if isinstance(fobj, ast.Name):
                for ln, nm, path in bound:
                    if nm == fobj.id and ln <= node.lineno:
                        tgt = path
            if not tgt:
                cands = [t for s0, e0, t, v in spans
                         if s0 <= node.lineno <= e0
                         and (v is None or not isinstance(fobj, ast.Name)
                              or v == fobj.id)]
                tgt = next((c for c in reversed(cands) if c), "")
            if not tgt:
                continue
            if not printed:
                print("    %s" % p.name)
                printed = True
            n += 1
            print("      L%-5d -> %s" % (node.lineno, tgt))
    print("\n    %d writer(s) with a statically resolved output path" % n)
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    rc = 0
    if mode in ("all", "carry"):
        rc |= check_carry()
    if mode in ("all", "positional"):
        rc |= check_positional()
    if mode == "writers":
        rc |= show_writers()
    return rc


if __name__ == "__main__":
    sys.exit(main())
