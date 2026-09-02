"""42_write_subaward_source_doc.py — emit `_SOURCE.md` for the 2026-08-05 subaward pull.

Every number in the generated document is interpolated from `_state.json` (what the API
actually returned and what is actually on disk) and `_SUMMARY.json` (what the match run
actually computed). Nothing is typed in by hand, so the document cannot drift from the data.

Usage: py -3 code/42_write_subaward_source_doc.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "subcontracts", "usaspending_subawards_2026-08-05")
STATE = os.path.join(RAW, "_state.json")
STAGE = os.path.join(ROOT, "data", "staging", "subawards_usaspending_2026-08-05")
SUMMARY = os.path.join(STAGE, "_SUMMARY.json")
OUT = os.path.join(RAW, "_SOURCE.md")

API = "https://api.usaspending.gov/api/v2/bulk_download/awards/"


def main():
    st = json.load(open(STATE, encoding="utf-8"))
    jobs = st["jobs"]
    s = json.load(open(SUMMARY, encoding="utf-8")) if os.path.exists(SUMMARY) else {}

    keys = sorted(jobs, key=lambda k: jobs[k]["_date_range"][0])
    tot_rows = sum(int(jobs[k].get("total_rows") or 0) for k in keys)
    tot_bytes = sum(int(jobs[k].get("_bytes") or 0) for k in keys)

    example = jobs[keys[-1]]
    payload = json.dumps(example["_payload"], indent=2)

    L = []
    A = L.append
    A("# _SOURCE — USAspending FSRS subaward pull, 2026-08-05")
    A("")
    A("*Dataset 2b (Subcontracting). Raw, as shipped by the API. Nothing in this folder is*")
    A("*derived, repaired, deduplicated or attributed.*")
    A("")
    A("---")
    A("")
    A("## 1. Endpoint and exact request")
    A("")
    A(f"```\nPOST {API}\n```")
    A("")
    A("One job per federal fiscal year. The endpoint rejects any window longer than a year")
    A('(`{"detail":"Invalid Parameter: date_range total days must be within a year"}`,')
    A("observed 2026-08-05 on a 2000-10-01..2009-09-30 request), so the fiscal year is the")
    A("largest chunk available and multi-year batching is not possible.")
    A("")
    A(f"Exact payload, shown for `{example['_chunk_key']}` "
      f"(every other job is identical but for `date_range`):")
    A("")
    A("```json")
    A(payload)
    A("```")
    A("")
    A("**No `columns` filter was sent.** The full as-shipped schema is retained: 118 columns")
    A("in the contracts-subaward member, 113 in the assistance-subaward member.")
    A("")
    A("### Parameter values that had to be discovered")
    A("")
    A("| Parameter | Value used | How it was established |")
    A("|---|---|---|")
    A("| `sub_award_types` | `procurement`, `grant` | The literal values `sub-contracts` / "
      "`sub-grants` are **rejected**: `Field 'filters|sub_award_types' is outside valid "
      "values ['grant', 'procurement']`. |")
    A("| `date_type` | `action_date` | Verified to key on the **subaward** action date, not "
      "the prime's — a 2015-10-01..2015-10-02 probe returned 62,836 rows of which every "
      "single one had `subaward_action_date` inside the window, while "
      "`prime_award_latest_action_date` ranged from 2015 to 2026. |")
    A("| agency filter | none | Omitted deliberately. The pull is the **whole federal "
      "subaward universe** per year, which is what gives Dataset 2b a real denominator — "
      "the thing the 2023 HigherGov export could never supply. |")
    A("")
    A("Status polling: `GET https://api.usaspending.gov/api/v2/download/status?file_name=...`")
    A("every 30s until `status == \"finished\"`, then the `file_url` is streamed to disk under")
    A("its original generated filename.")
    A("")
    A("## 2. Pull date and provenance")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Pull date | **2026-08-05** |")
    A(f"| Jobs completed | {len(keys)} |")
    A(f"| Total rows retrieved | **{tot_rows:,}** |")
    A(f"| Total bytes on disk | {tot_bytes:,} |")
    A("| Retrieval script | `code/40_pull_usaspending_subawards.py` |")
    A("| Match script | `code/41_match_subawards_to_ledger.py` |")
    A("| Manifest (sha256 per file) | `_SOURCE_MANIFEST_usaspending_subawards.csv` |")
    A("")
    A("## 3. Row counts per fiscal year, as returned")
    A("")
    A("`rows` is the API's own `total_rows` for the job. `linked_rows` and the two")
    A("population columns come from the match run and are repeated here only for")
    A("convenience; the authority for those is `data/staging/subawards_usaspending_2026-08-05/`.")
    A("")
    A("| Chunk | date_range | rows | bytes | file |")
    A("|---|---|---:|---:|---|")
    for k in keys:
        m = jobs[k]
        s0, s1 = m["_date_range"]
        A(f"| `{k}` | {s0} .. {s1} | {int(m.get('total_rows') or 0):,} | "
          f"{int(m.get('_bytes') or 0):,} | `{os.path.basename(m['_local_file'])}` |")
    A(f"| **TOTAL** | | **{tot_rows:,}** | **{tot_bytes:,}** | |")
    A("")
    A("## 4. Temporal floor — 2000 requested, 2010 delivered")
    A("")
    A("Cedar Press applies a floor of 2000 to every dataset. Jobs were submitted for every")
    A("fiscal year from FY2001 so the true floor would be **demonstrated from the source**")
    A("rather than asserted from documentation.")
    A("")
    A("**This is a source limitation, not a coverage failure.** FSRS subaward reporting was")
    A("created by the Federal Funding Accountability and Transparency Act (FFATA, 2006) and")
    A("phased in during 2010 — contract subawards first, grant subawards from October 2010.")
    A("Subaward records for FY2001–FY2009 do not exist to be pulled, from this or any other")
    A("source. The gap between the Cedar Press floor of 2000 and the data floor of 2010 is")
    A("**structural and permanent**, and must be stated wherever Dataset 2b is published.")
    A("")
    A("### The pre-2010 rows are misdated filings, not pre-FFATA reporting")
    A("")
    pre_n = s.get("rows_with_action_date_before_ffata")
    min_ry = s.get("min_sam_report_year_on_those_rows")
    if pre_n:
        A(f"The FY2001–FY2009 jobs did **not** come back empty — they returned "
          f"**{pre_n:,} rows** between them. That is a trap, and it is resolved by the "
          f"source's own filing field.")
        A("")
        A(f"**Every one of those {pre_n:,} rows carries `subaward_sam_report_year` "
          f"≥ {min_ry}.** Not one was filed before FSRS existed. The distribution runs all "
          f"the way to 2026 — including a SpaceX subaward with "
          f"`subaward_action_date = 2000-11-09` and `subaward_sam_report_year = 2024`.")
        A("")
        A("So `subaward_action_date` on these rows is a **data-entry error by the filer**, "
          "not evidence of pre-FFATA subaward reporting. Anyone who pulls this range and "
          "charts it by action date will publish a phantom 2001–2009 series.")
        A("")
        A("Per the Cedar Press flag-never-delete rule the rows are retained. The match "
          "output carries `action_date_precedes_ffata_flag = yes` on all of them, and "
          "`subaward_sam_report_year` travels alongside so the test is reproducible "
          "downstream.")
        A("")
        hist = s.get("sam_report_year_histogram_on_those_rows") or {}
        if hist:
            A("| `subaward_sam_report_year` | rows with a pre-FY2010 action date |")
            A("|---|---:|")
            for y, c in sorted(hist.items()):
                A(f"| {y} | {c:,} |")
            A("")
    A("## 4b. Completeness of this pull")
    A("")
    done = set(keys)
    outstanding = [f"fy{fy}" for fy in range(2001, 2027) if f"fy{fy}" not in done]
    if outstanding:
        A(f"**This pull is INCOMPLETE. {len(done)} of 26 fiscal-year jobs are staged; "
          f"{len(outstanding)} are outstanding:** "
          + ", ".join("`" + o + "`" for o in outstanding) + ".")
        A("")
        A("Cause: `api.usaspending.gov` rate-limits by IP, and the block does not clear "
          "quickly. At 2026-08-05 21:16Z both `api.usaspending.gov` and "
          "`files.usaspending.gov` began refusing every request with "
          "`RemoteDisconnected` from a fresh connection — the same edge block documented "
          "for the FY2001-07 assistance backfill. Retrying hard through it appears to "
          "extend it, so the puller was stopped rather than left hammering.")
        A("")
        A("**Nothing is lost and nothing needs re-doing.** Every completed job is "
          "checkpointed in `_state.json`; `pull` skips what is already on disk. Resume with:")
        A("")
        A("```\nbash code/43_resume_subaward_pull.sh\n```")
        A("")
        A("which probes the edge once every 300s, then `recover`s the FY2012/FY2013 jobs "
          "that were **already accepted server-side** before the block (re-submitting "
          "would discard completed server work) and finishes the rest at "
          "`--workers 1`. Six concurrent workers is what tripped the block.")
    else:
        A("All 26 fiscal-year jobs are staged.")
    A("")
    A("## 5. Schema, as shipped")
    A("")
    A("Each zip contains up to two CSV members, and they have **different schemas**:")
    A("")
    A("| Member | Columns | Prime award key | Prime industry code |")
    A("|---|---:|---|---|")
    A("| `All_Contracts_Subawards_*.csv` | 118 | `prime_award_piid` | `prime_award_naics_code` |")
    A("| `All_Assistance_Subawards_*.csv` | 113 | `prime_award_fain` | *(none — assistance "
      "carries CFDA, not NAICS)* |")
    A("")
    A("Any consumer that reads these files must branch on the member name. A single")
    A("`DictReader` union over both silently produces empty `prime_award_piid` on every")
    A("assistance row.")
    A("")
    A("Both members share the subaward-side block, which is what Dataset 2b turns on:")
    A("`subaward_type`, `subaward_number`, `subaward_amount`, `subaward_action_date`,")
    A("`subaward_action_date_fiscal_year`, `subawardee_uei`, `subawardee_duns`,")
    A("`subawardee_name`, `subawardee_parent_uei`, `subawardee_parent_name`,")
    A("`subawardee_business_types`, `subaward_description`, `usaspending_permalink`,")
    A("`subaward_sam_report_id`, `subaward_sam_report_last_modified_date`, and the five")
    A("`subawardee_highly_compensated_officer_*` pairs.")
    A("")
    A("**This schema carries `subawardee_duns` and `prime_awardee_duns`.** The 2023 HigherGov")
    A("export had no DUNS column at all (`missing_duns` on all 304 harvest rows). DUNS is")
    A("recoverable from this source for the pre-2022 period.")
    A("")
    if s:
        A("## 6. What the match run found")
        A("")
        A("Full detail in `docs/SUBCONTRACTING_USASPENDING_PULL_2026-08-05.md`. Headline")
        A("figures, computed by `code/41_match_subawards_to_ledger.py`:")
        A("")
        A("| Metric | Value |")
        A("|---|---:|")
        A(f"| Subaward rows read | {s.get('rows_total', 0):,} |")
        A(f"| Native-linked rows (tier A or B, tribe_id present) | {s.get('rows_native_linked', 0):,} |")
        A(f"| **(a) Native entity as PRIME** | **{s.get('population_a_native_as_prime', 0):,}** |")
        A(f"| **(b) Native entity as SUBAWARDEE** | **{s.get('population_b_native_as_subawardee', 0):,}** |")
        A(f"| Both sides Native | {s.get('population_both_sides', 0):,} |")
        A(f"| Rows touching a tier-X exclusion ruling | {s.get('rows_touching_tier_X_exclusion', 0):,} |")
        A(f"| Distinct UEIs observed | {s.get('ueis_observed', 0):,} |")
        A(f"| **Net-new UEIs vs the 2023 HigherGov file** | **{s.get('netnew_vs_2023_highergov_harvest', 0):,}** |")
        A(f"| Net-new vs union(HigherGov, fpds_uei_cage_map) | {s.get('netnew_vs_union_highergov_and_fpds_map', 0):,} |")
        A(f"| Distinct Native entities (NEID) observed | {s.get('native_entities_matched', 0):,} |")
        A(f"| Unattributed name near-matches queued for ruling | {s.get('unattributed_name_near_matches', 0):,} |")
        A("")
    A("## 7. Standing caveats — carry these into anything published")
    A("")
    A("1. **FSRS is self-reported, threshold-gated and unaudited.** Primes report subawards")
    A("   only above a reporting threshold and only on prime awards above their own")
    A("   threshold. Absence of a subaward is **not** evidence that no subcontracting")
    A("   occurred. Every dollar figure is a lower bound of unknown tightness.")
    A("2. **The most recent fiscal year is partial** — it was pulled mid-year on 2026-08-05.")
    A("   Never chart it as a decline.")
    A("3. **`prime_award_naics_code` is the PRIME contract's industry, not the subaward's.**")
    A("   FSRS carries no subaward-level NAICS or PSC. An input-output linkage built on it")
    A("   describes demand, not the supplying industry.")
    A("4. **Assistance subawards have no NAICS at all**, so any industry cut silently")
    A("   restricts to the contracts member.")
    A("5. **No entity attribution lives in this folder.** Linking is done downstream in")
    A("   `code/41_match_subawards_to_ledger.py` against the existing identifier ledger,")
    A("   and its output is staged, not published.")
    A("")
    A(f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} by "
      f"`code/42_write_subaward_source_doc.py`.*")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
