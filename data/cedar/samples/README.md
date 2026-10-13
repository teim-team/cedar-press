> **2026-10-04: the producer samples now live one directory down.** The subdirectories here,
> `<collection>/spreadsheet__10.csv`, are the producer's pinned samples, moved out of
> `public/data/cedar/samples/` so the site no longer serves them (they carry the multi-table
> layout and, for NEED, retired `CEDAR-NEST-` IDs). The API and
> `scripts/render_sample_downloads.py` read them and render each as the collection's customer
> table, `public/data/cedar/downloads/<collection>.csv`, which is the only sample the site serves.

The 2026-09-02 extracts that used to sit at the top level here (`*__sample.csv`)
and this README's measurements of them are kept in git history at the tag `data-workspace-final`.
