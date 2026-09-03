# Knowing who reads Cedar Press

Accounts arrive from a Tribal Business News subscription, which means the
service starts out knowing an email address and nothing else. A tribal
chairman, a lender's underwriter and a reporter all read the same shelf, and
without knowing which is which the roadmap cannot tell a request that matters
to a nation from one that matters to a vendor.

This is how the service learns who is reading, and where the line is.

## What is collected

Two answers, given by the subscriber, on the overview:

| Field | Values | Why |
| --- | --- | --- |
| `organizationKind` | Tribal government, tribal enterprise, ANC/NHO, Native nonprofit, federal, state or local, lender or investor, advisory firm, media, academic, other | Which audience a collection serves |
| `role` | The seat, from `subscriberProfile.ROLES` | Whether the reader decides, analyzes or reports |
| `organization` | Free text, optional | So a data request can be attributed |

The email's domain seeds a likely answer — `*.nsn.gov` and `*-nsn.gov` read
as tribal government, `*.gov` and `*.mil` as federal, `*.edu` as academic —
which the subscriber then confirms or corrects. The guess is a shortcut, not
a conclusion, and a commercial domain gets no guess at all.

Connected, the profile is a column on the subscriber record, so the roadmap
can query it across the subscription. Standalone, it stays in the browser and
the card says the answers are not saved to an account.

## What analytics receives

Datadog RUM gets **segments, not people**: tier, organization kind, role, and
the class of the email's domain (`federal`, never `bia.gov`). No address, and
no organization name — a small newsroom's name in an analytics tool
identifies the reader on its own. `subscriberProfile.profileSegments` is the
only thing telemetry may send, and a unit test asserts that its output
contains no address, domain or organization name.

RUM is the wrong place to keep this anyway: it is sampled and it expires.
The subscriber record is where "which tribal governments opened the
contracting collection last quarter" gets answered; RUM answers "is the
service fast and does it break."

## Third-party enrichment: deliberately not built

An obvious next step is to send subscriber addresses to an enrichment vendor
(Clearbit, Apollo, ZoomInfo and the like) and buy back employer and job
title. That is not wired here, and it should not be added without a decision
made deliberately, because:

- **It is a disclosure.** Sending a subscriber list to a data broker
  discloses who reads Cedar Press to a company with no relationship to
  Tribal Business News or Lumecon, and that list is itself commercially
  sensitive — it names the tribal governments and lenders paying attention
  to Indian Country's economy.
- **It contradicts the argument.** The product's case is that Indian
  Country's data deserves careful, sovereign handling. Quietly profiling
  Native readers through a broker is the practice the service exists to
  contrast with, and it reads that way if it surfaces.
- **The data is worse.** Enrichment infers a title from a company record and
  is routinely stale or wrong at exactly the organizations that matter here —
  tribal governments and enterprises are thinly covered by commercial
  databases. A reader naming their own seat is better data.
- **It carries obligations.** Purchased personal data brings CCPA/CPRA
  disclosure and deletion duties and, for anyone in scope, GDPR ones.

If enrichment is still wanted, the shape that survives review is: run it
**server-side** against organizations rather than individuals (the domain, not
the person), disclose it in the privacy policy, and keep it out of the
browser entirely. That is a platform decision with counsel involved, not a
client feature.

## Better signals, already available

- **Requests.** The tribal data request and research access pages are
  first-party statements of need, attributable to an organization.
- **What gets opened.** `press.collection_viewed` and
  `press.collection_downloaded` carry the collection and the shelf, and
  segment by organization kind — which answers "who wants what" directly.
- **The upgrade boundary.** `press.locked_collection_tapped` names the
  collections a tier does not include that its readers keep reaching for.
