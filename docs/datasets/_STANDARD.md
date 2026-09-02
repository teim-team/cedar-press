# The dataset standard — twelve points

*Generated from `code/526_dataset_standard.py`. The shape every Cedar dataset takes. See ADR-009 to ADR-013.*

```
THE SHAPE, in one place (twelve points)
---------------------------------------
  C1  grain declared AND validated on the full file
  C2  primary key + join keys validate; cardinality is a promise, not a guess
  C3  literal duplicates removed, or the distinguishing dimension declared
  C4  entity attachment WHERE THE SUBJECT IS AN ENTITY (ADR-010 - a bill
      affecting all of Indian Country has none, and that is correct)
  C5  every harvested row lands in a NAMED disposition bucket
  C6  unresolved identity conflicts never ship as definite facts
  C7  no double-counting path; join cardinality honest
  C8  ONE documented rebuild that does not destroy later enrichment
  C9  an update runbook another session can execute from the document alone
  C10 regression + semantic-diff gates cover the outputs
  C11 column hygiene - no always-empty columns, every column in a codebook,
      raw source codes decoded or documented (ADR-011)
  C12 inclusion basis - every row can answer WHY IT IS IN CEDAR (ADR-013);
      for a dataset that will never have an entity, this is the ONLY evidence
      of scope and therefore the load-bearing column

```
