# NEST → NEED: the collection rename

**Decided 2026-09-10 by the owner.** The tenth Cedar Press collection, built
2026-09-02 as `nest` — "NEST: Native Enterprise Structures and Ties" — is now
`need`, **Cedar Native Entity Enterprise Dataset (NEED)**. This file is the
binding: it says what changed, what did not, and why the two halves differ.

## Why the name moved

"Native entity enterprise dataset" is a plain description of contents, not a
brand, and no one holds exclusive rights in it by using it. The Minneapolis Fed
publishes a dataset under close to that description, so the risk here is
confusion rather than legality: a reader who meets a bare "Native Entity
Enterprise Dataset" may assume ours is theirs, affiliated with it, or derived
from it. The formal name therefore leads with **Cedar**, which is the half a
reader can attribute and the half this project can build recognition around.
The lowercase phrase stays available as ordinary description. Where the two
datasets are ever cited side by side, the citation carries the source note.

## What changed

| kind | before | after |
|---|---|---|
| collection id / `cedar_id` | `nest` | `need` |
| formal name | NEST: Native Enterprise Structures and Ties | Cedar Native Entity Enterprise Dataset (NEED) |
| short name | `NEST` | `NEED` |
| flagship table | `nest_enterprises.csv` | `need_enterprises.csv` |
| relations table | `nest_enterprise_relations.csv` | `need_enterprise_relations.csv` |
| dual-role table | `nest_entity_dual_role.csv` | `need_entity_dual_role.csv` |
| published columns | `is_nest_owner_hub`, `n_nest_enterprises_owned` | `is_need_owner_hub`, `n_need_enterprises_owned` |
| duplicate-group label | `NESTDUP-nnnn` | `NEEDDUP-nnnn` |
| customer file | `dist/customer/nest.csv` | `dist/customer/need.csv` |
| researcher guide | `docs/guides/nest.md` | `docs/guides/need.md` |
| methodology paper | `docs/methodology/nest.md` | `docs/methodology/need.md` |
| build log | `docs/NEST_BUILD_LOG.md` | `docs/NEED_BUILD_LOG.md` |
| corroboration record | `docs/NEST_CORROBORATION.json` | `docs/NEED_CORROBORATION.json` |
| pipeline scripts | `code/1102_nest_*`, `1130_nest_*`, `1133_nest_*`, `1157_nest_*` | the same numbers, `_need_` |

Everything the repository holds is renamed. The site catalog, the collection
manifest, the descriptors, the release records, the dataset contracts, the
codebook, the field map, the schema tree, the structured data in `index.html`
and the server's press payload all read `need` now, and the test suites pass
against it.

## What did NOT change, and why

**Minted identifiers keep the letters they were minted with.** An id is
permanent — that is the whole content of `docs/IDENTIFIER_STANDARD.md`, and the
`CEDAR-HOLD` entry in `code/cedar_ids.py` is the project's own precedent: a
prefix is never reused and never rewritten. Rewriting a prefix after issue
would silently invalidate every id already quoted in a release, a customer
file, a codebook or a researcher's citation.

So these stay as they are, and are read as namespaces rather than as the
collection's current name:

| kept | what it is | why |
|---|---|---|
| `CEDAR-NEST-nnnnnn-CC` | the enterprise register prefix, allocated under lock in `code/cedar_ids.py` | issued and shipped in v0 and v1, through at least `CEDAR-NEST-006088-TN`; the counter lives in `data/spine/_id_registry.json`, which git does not track |
| `NESTREL-XXXXXXXXXXXXXX` | the enterprise-edge id, a content hash of the assertion (`code/1072`, line 1890) | deterministic: renaming the prefix rewrites every edge id for rows that did not change |
| `NEST-OWNER-V6-*`, `OWNER-V6-NEST-2026-09-02`, `QA-NEST-SOURCEDOC`, `NEST-RELATIONSHIP-RESOLUTION-QA-2026-09-02`, `NEST-OWNERV6-BRAND-GUARD-2026-09-02` | workstream and QA run ids recorded on 2026-09-02 | a run id names a run that happened; it is not a label that can be restyled afterwards |
| `ADR-032-NEST-DUAL-ROLE` | the architecture decision anchor in `docs/ARCHITECTURE_DECISIONS.md` | anchors are linked from outside the file |
| `NEST-1` | the owner decision queue item in `review/OWNER_DECISION_QUEUE.md` | an issued reference id, cited from `code/1122` |

One value that *looks* like one of those did move: the
`duplicate_name_variant_group` label, `NESTDUP-nnnn` → `NEEDDUP-nnnn`
(`code/1102`, line 302). It is a running counter over sorted groups,
recomputed from scratch on every build, so its numbering already shifts the
moment a row is added. That is a per-build label, not an identifier, and
nothing joins on it.

The v0 (2026-09-02) and v1 (2026-09-04) release records now carry the new name,
because they are records of *this* collection and a reader looking up either
version needs to find it under the name the catalog shows. The rows those
releases shipped are unchanged, and the ids in them still read `CEDAR-NEST-`.

One further occurrence of the word is not this collection at all and was left
alone: `code/524_universe_gap.py` matches `language nest`, the term for a
Native language immersion school.

## What the operator has to do outside the repository

The pipeline reads and writes a working tree that git does not track. Renaming
the code without renaming those files leaves the next build looking for paths
that do not exist. Rename, in the Cedar Press working directory:

    data/clean/nest_enterprises.csv            -> need_enterprises.csv
    data/clean/nest_enterprise_relations.csv   -> need_enterprise_relations.csv
    data/clean/nest_entity_dual_role.csv       -> need_entity_dual_role.csv
    data/clean/codebook/18a_nest_enterprises.csv         -> 18a_need_enterprises.csv
    data/clean/codebook/18b_nest_enterprise_relations.csv -> 18b_need_enterprise_relations.csv
    data/spine/cedar_nest_id_register.csv      -> cedar_need_id_register.csv
    data/staging/nest/                         -> data/staging/need/
    data/staging/nest_owner_v6/                -> data/staging/need_owner_v6/
    data/staging/nest_owner_v6/nest_not_in_owner.csv -> need_not_in_owner.csv
    data/staging/native_business_sweep_1070/held_for_nest_ownership.csv
                                               -> held_for_need_ownership.csv
    dist/customer/nest.csv                     -> need.csv
    dist/customer/nest__CODEBOOK.md            -> need__CODEBOOK.md
    dist/review/spreadsheets/nest/             -> dist/review/spreadsheets/need/

The two published columns are renamed in the writer, so the next build of
`need_entity_dual_role.csv` emits `is_need_owner_hub` and
`n_need_enterprises_owned`. A consumer holding v1 has the old spelling; that is
what a version number is for.
