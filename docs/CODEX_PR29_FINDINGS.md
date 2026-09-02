
==============================================================================
[1] data/cedar/README.md  line 40  id=3911087281
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Strip metadata before constructing CollectionDataset**

The advertised `CollectionDataset(**descriptor)` call fails for every object: each descriptor also contains `cedar` and `needs_copy`, while `server/cedar_press/collections.py` defines neither as a dataclass field, so Python raises `TypeError` on the first unsupported keyword. Either publish only the dataclass fields or document and implement the projection required before deserialization.

Useful? React with 👍 / 👎.

==============================================================================
[2] data/cedar/samples/contractors__sample.csv  line 11  id=3911087284
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Correct the Old Harbor award's entity attribution**

For this newly sampled award, `parent_name` identifies Old Harbor Native Corporation, but `canonical_name` and `cedar_uid` assign it to Three Affiliated. When buyers group contractor records by the Cedar identity as the descriptor directs, this transaction is therefore credited to an unrelated nation; correct the source mapping and regenerate the sample.

Useful? React with 👍 / 👎.

==============================================================================
[3] data/cedar/collection_descriptors.json  line 310  id=3911087288
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Restore the subcontracting coverage blocker**

The commit removes the C4 blocker even though `data/cedar/README.md` still reports that only 42% of subcontracting's entity-bearing rows carry a Cedar ID and promises that every blocker is named in the descriptor. A consumer relying on this JSON now misses the unresolved identity coverage affecting 58% of rows; retain that blocker unless the underlying coverage was actually fixed.

Useful? React with 👍 / 👎.

==============================================================================
[4] data/cedar/samples/contractors__sample.csv  line 2  id=3911087295
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Clear the self-referential parent contract number**

For this standalone `DADA1098C0035` award, the newly added `parent_contract_number` is identical to `contract_number`. The accompanying README defines the parent as the referenced IDV and says standalone PIIDs have no parent, so this value fabricates a self-parent relationship and invalidates consumers' parent/child classification; leave the parent empty for standalone awards.

Useful? React with 👍 / 👎.

==============================================================================
[5] data/cedar/samples/gaming__sample.csv  line 10  id=3911087300
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Preserve both operating tribes for jointly run facilities**

This facility names both the Modoc Tribe of Oklahoma and the Miami Tribe of Oklahoma in `tribe`, but exposes only one `cedar_uid`. Because the descriptor says facilities are keyed to their operating tribes, entity-based filtering can associate The Stables with only one of its two operators and omit it from the other tribe's results; represent the relationship with both entity IDs or a facility-to-tribe bridge.

Useful? React with 👍 / 👎.

==============================================================================
[6] data/cedar/samples/nagpra__sample.csv  line 6  id=3911087308
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Remove notice-type text from the institution name**

For document `2017-20294`, `institution_name` is emitted as `Cultural Items: U.S. Army Corps of Engineers, Omaha District`; `Cultural Items:` is part of the notice heading rather than the institution. Institution grouping and matching will therefore treat this as a different organization from other Army Corps records, so the parser should strip the residual notice-type prefix.

Useful? React with 👍 / 👎.

==============================================================================
[7] data/cedar/README.md  line 33  id=3911087315
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Map the owned sample to its shipped dataset ID**

The commit says `owned` is now the ID that ships, but the sample remains `native-owned-businesses__sample.csv` and the sample index still uses the old ID. A repo-wide search finds neither an `owned__sample.csv` file nor a mapping for it, while the other twelve descriptor IDs match their sample filenames, so an ID-based manifest consumer cannot locate the `owned` sample; rename it or add an explicit mapping.

Useful? React with 👍 / 👎.

==============================================================================
[8] data/cedar/samples/nagpra__sample.csv  line 10  id=3911087317
==============================================================================
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Preserve locations for every institution in a notice**

This notice stores several institutions spanning South Carolina, North Carolina, and Connecticut in one `institution_name`, but the singular `institution_city` and `institution_state` fields retain only New Haven, CT. Institution- or geography-level filtering will consequently assign all participating institutions to Yale's location and cannot recover the other name/location relationships; emit one institution association per row or use a structured bridge.

Useful? React with 👍 / 👎.
