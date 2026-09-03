# Dataset discovery — 2026-09-02 round: Native business orgs, chambers and awards

Catch-up round covering the 08-30/08-31/09-01 firings (session was busy on
landing-page work); one frame, one sweep. 9 rows in
`dataset_discovery_2026-09-02.jsonl` (WebSearch-only evidence grade — every
URL literal from results, nothing constructed).

## What the frame added

The registry already carries chambers for NM, WA, MN, OK, AZ, CA, CO, the
Northwest and Hawaiʻi. This round filled the gaps and found two genuinely new
source *classes*:

- **Award programs as enumeration channels.** Montana's Indian Equity Fund
  publishes grantee announcements naming Native-owned businesses (26 in one
  round), year over year — the announcement archive is the dataset. And
  **NAFOA's Deal of the Year** (annual since 2008) is a direct validation
  feed for the Cedar deals dataset: tribe, counterparties, instrument and
  dollar value, third-party confirmed (e.g. $390M River Rock 2026, $110M
  Ione Band 2025, $800M Morongo Transmission 2023), with trade-press
  coverage back to 2007.
- **Chamber gap-fills:** NACC-Illinois has a live member directory
  (nacc-il.org/member-directory — first Great Lakes/Chicago chamber row);
  AICCW-Wisconsin runs a ChamberMaster platform (directory root unconfirmed —
  do not construct the /list URL, verify at first fetch); NCAIED's Native
  Edge portal (edge.ncaied.org) is the concrete enumerable surface behind
  the RES operator, likely account-gated.

## Honest negatives and boundaries

- **AICCT (Texas)**: chamber active since 1987, no public member directory
  found — outreach-lead shaped, recorded so it is not re-proposed.
- **MIBA (Montana)**: 2006 Fed article says a directory was being compiled;
  none surfaced 20 years on.
- **AIBL** business directory profiles *people* (student/professional org) —
  person boundary applies; Discovery Only at best.
- **Native Business Top 50 (2019)**: historical editorial snapshot, persons
  with firms; person boundary on the individuals.

No registry rows were added or changed; all promotion decisions wait on
fetchability and the next wave decision.
