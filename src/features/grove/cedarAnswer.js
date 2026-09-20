// What the line under a Cedar answer says, decided outside the component.
//
// WHY THIS IS NOT JUST JSX IN THE PANEL
// It was, and a real defect rode in on that. `PressCedarFab` rendered "View
// supporting records" under every release-grounded answer, and once the
// server started answering for collections a subscription does *not* include
// — a dataset description, read off the release, with no retrieval behind it
// — that link appeared one sentence after the answer had said the records
// open with Cedar Press+. The panel invited the reader into a table the
// server had just declined to open for them.
//
// A lock rendered in React is not authorization, and the inverse is the same
// mistake in the other direction: a link rendered in React is not access.
// The decision is small, it is the one thing in this panel that can
// contradict the entitlement, and it is testable only if it is a function.
// So it is one, and `cedarAnswer.test.js` checks the invariant directly:
// nothing that is not opened offers records.

/** The release an answer was read from, as a person would name it. */
export function releaseOf(basis) {
  return [basis?.collectionName, basis?.version].filter(Boolean).join(" ");
}

/**
 * What to say under an answer, or `null` when there is nothing to say.
 *
 * `basis.kind` says what produced the answer; `basis.opened` says whether
 * this subscription reaches the records behind it. Two axes, deliberately,
 * because the locked collection is the combination that needs both: its
 * description is a true reading of its release *and* its records are shut.
 * Folding that into `kind` would lose the citation.
 *
 * Returns `{ tone, release, updated, records }`:
 *
 *   tone         "release"      read off the release, records reachable
 *                "description"  read off the release, records not included
 *                "synthesis"    Cedar composed it; the scope is real
 *                "review"       identity or scope is ambiguous; no answer
 *   release      the release named, or "" when the basis carries no name
 *   updated      the release date, or null
 *   records      the collection id to link records for, or null
 *
 * `records` is null for everything but `release`. That is the invariant, and
 * it is stated once here rather than at each call site.
 */
export function answerSource(basis) {
  if (!basis?.kind) return null;
  const release = releaseOf(basis);
  if (basis.kind === "review") {
    return { tone: "review", release, updated: null, records: null };
  }
  if (basis.kind !== "release") {
    return { tone: "synthesis", release, updated: null, records: null };
  }
  // `opened` is absent on an older server. Treating a missing field as
  // "opened" is the permissive default, and the permissive default is the
  // wrong one for an access decision: an omitted field is not a grant.
  const opened = basis.opened === true;
  return {
    tone: opened ? "release" : "description",
    release,
    updated: basis.updated || null,
    records: opened ? basis.collectionId || null : null,
  };
}
