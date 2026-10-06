# Archived workspace scripts

Moved here on 2026-10-02, not deleted. Each script below had **zero references
of any kind** in the Git-tracked repository (no Makefile target, CI job, other
script, `package.json` script, documented command, journal entry, data or
configuration file; no number-free-stem or number-keyed loader reference),
**wrote no tracked artifact** (every output named is under `data/clean/`,
`data/staging/`, `dist/` or `review/`, all gitignored), was not `ACTIVE` in the
521 census, was not on `cedar_pipeline.NEVER_RUN`, and sat in no table contract
or ordering. The measurement is `docs/CODE_REFERENCE_GRAPH_2026-10-02.json`
(`python3 server/tests/code_reference_graph.py`); the 521 census agreed
(`mentions = 0`, `mentioned_outside_history = 0` for every one).

Referenced-by-nothing is still not dead (`docs/ARCHIVE_CANDIDATES.md`): a probe
a person runs by hand has no inbound reference. That is why this is a move, in
Git, with the path recorded, and why the scripts keep their numbers. Restore one
with `git mv code/archive/<script> code/<script>` and re-run
`python3 code/521_inventory.py scripts-only`. No script here is a producer of a
served collection; the shard F chain (590 to 602) is a 2026-09-01 harvest of
organisational-layer web candidates whose outputs live under
`data/staging/tribe_harvest/shard_f/` on the owner's machine, not in Git.

"Last build-log mention" is measured over every tracked `docs/*.md`: none of
these scripts is named in any build log, which is the condition that put them
here. The git date is the join of the two trees (`2ba9baa`, 2026-09-05); the
census `last_modified` is the file's mtime when the census ran.

| Script | Lines | Census status, role, writer risk | Writes (untracked) | Last build-log mention | Git history |
| --- | ---: | --- | --- | --- | --- |
| `1172_codebook_block_generator.py` | 238 | REQUIRES-REVIEW, unresolved, P3 no detected write | none detected | none | `2ba9baa` 2026-09-05, 1 commit |
| `1175_write_id_system_doc.py` | 276 | REQUIRES-REVIEW, unresolved, P3 no detected write | `dist/qc_review/2_how_cedar_ids_work.docx` | none | `2ba9baa` 2026-09-05, 1 commit |
| `1178_sentinel_null_and_recount.py` | 15 | REQUIRES-REVIEW, unresolved, P3 no detected write | none detected | none | `2ba9baa` 2026-09-05, 1 commit |
| `1179_cross_table_key_consistency.py` | 789 | REQUIRES-REVIEW, unresolved, P1 undeclared governed write candidate | `data/clean/federal_funding_transactions.csv`, `data/clean/cedar_identifier_ledger_final.csv` (in `w` mode), `1179_cross_table_key_gap_*.csv` | none | `2ba9baa` 2026-09-05, 1 commit |
| `1182_stream_official_names.py` | 187 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `probe.csv` | none | `2ba9baa` 2026-09-05, 1 commit |
| `530_shard_b_tribe_web_probe.py` | 202 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `data/staging/tribe_harvest/shard_b/` | none | `2ba9baa` 2026-09-05, 1 commit |
| `536_shard_e_newsletters.py` | 248 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `newsletters.jsonl` under the shard E staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `584_register_labor_codebook.py` | 278 | REQUIRES-REVIEW, unresolved, P3 no detected write | none detected (registers a codebook block through `cedar_codebook`) | none | `2ba9baa` 2026-09-05, 1 commit |
| `590_shard_f_org_slice.py` | 189 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `data/staging/tribe_harvest/shard_f/_slice.json` | none | `2ba9baa` 2026-09-05, 1 commit |
| `591_shard_f_ihs_uio_register.py` | 145 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `data/staging/tribe_harvest/shard_f/ihs_uio_register.jsonl` | none | `2ba9baa` 2026-09-05, 1 commit |
| `592_shard_f_ihs_selfgov_compacts.py` | 115 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `ihs_selfgov_compacts.jsonl` under the shard F staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `593_shard_f_candidates.py` | 222 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `_candidates.json` under the shard F staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `595_shard_f_org_web_reprobe.py` | 228 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | shard F staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `597_shard_f_org_rosters_finalise.py` | 144 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `data/staging/org_membership/shard_f.jsonl` | none | `2ba9baa` 2026-09-05, 1 commit |
| `598_shard_f_newsletters.py` | 243 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `newsletters.jsonl` under the shard F staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `600_shard_f_service_area.py` | 292 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `service_area_authority.jsonl` under the shard F staging directory | none | `2ba9baa` 2026-09-05, 1 commit |
| `601_shard_f_build_web_map.py` | 201 | REQUIRES-REVIEW, unresolved, P2 unresolved write target | `data/staging/tribe_web_map/shard_f.csv` | none | `2ba9baa` 2026-09-05, 1 commit |
| `602_shard_f_verify.py` | 170 | REQUIRES-REVIEW, unresolved, P3 no detected write | none detected (reads `data/spine/cedar_identity_register.csv`) | none | `2ba9baa` 2026-09-05, 1 commit |

Kept at the top of `code/`, although unreferenced by name, because a loader or a
document names them by number or by stem: `1185_deals_fact_check_2025_2026.py`
(`cedar_publication.deals_public_view` loads it as `_script("1185",
"deals_fact_check_2025_2026")`), `535_shard_e_match_candidates.py`,
`562_probe_atom_native_flags_pre2000.py`, `563_probe_atom_flag_content_by_era.py`,
`564_benchmark_reconciliation.py`, `565_unattributed_ruling_dollars.py`,
`566_pre2000_coverage_probe.py` and `567_stage_cicd_published_series.py`. The
graph records the referencing file for each.

This file is a catalogue of the scripts it names; the 521 census and the
reference graph both exclude it when they count references.
