/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Freshness. What release a collection is on, when it last changed, how often
 * it changes, and what changed in it.
 *
 * This is the reason Cedar is a subscription rather than a file you buy once.
 * A collection can be accurate when published and wrong a year later if nobody
 * maintains the organizations behind it, so "last updated" is a headline fact
 * about a collection, not a footnote inside a methodology paragraph. It lives
 * in metadata rather than in page copy so a page cannot go stale independently
 * of the thing it describes.
 *
 * TWO KINDS OF RELEASE
 * A data update adds records, corrects them, or extends coverage. A
 * methodology update changes inclusion rules, classification or resolution
 * logic, and can therefore change a number somebody already published. The
 * second kind is called out loudly, because silently changing consequential
 * methodology is how a research product loses researchers.
 *
 * CADENCE IS NOT UNIFORM
 * Federal Register moves when the agencies move; lobbying moves on filing
 * quarters. Forcing one cadence onto all of them would be a promise the
 * pipeline does not keep.
 */

/** How often a collection changes. The label is what a reader sees. */
export const CADENCE = Object.freeze({
  MONTHLY: "Updated monthly",
  QUARTERLY: "Updated quarterly",
  CONTINUOUS: "Updated continuously",
  ON_CHANGE: "Updated as records arrive",
  ANNUAL: "Updated annually",
});

/** A release changes the data, or it changes how the data is made. */
export const RELEASE_KIND = Object.freeze({
  DATA: "data",
  METHOD: "methodology",
});

/**
 * Per collection: where it is now, and how it got here.
 *
 * `changed` is written for a reader of the research product, not pulled from
 * a commit log. "Resolved 14 recipients to existing tribal enterprises" is
 * something a subscriber can act on; "bump parser to 2.3" is not.
 */
export const PRESS_RELEASES = Object.freeze({
  funding: Object.freeze({
    version: "v4.2",
    updated: "2026-08-06",
    cadence: CADENCE.MONTHLY,
    summary: "July awards added, with fourteen recipients resolved to existing tribal enterprises.",
    history: Object.freeze([
      Object.freeze({
        version: "v4.2",
        date: "2026-08-06",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added 386 newly reported awards through July 2026.",
          "Resolved 14 recipients to existing tribal enterprises.",
          "Added two newly identified subsidiaries.",
          "Corrected the historical affiliation of one recipient.",
        ]),
      }),
      Object.freeze({
        version: "v4.1",
        date: "2026-07-08",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added 412 awards through June 2026.",
          "Entity updates from the maintained identity layer affected 28 historical records.",
        ]),
      }),
      Object.freeze({
        version: "v4.0",
        date: "2026-06-04",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Extended the reconstructed archive back to 2001 using additional federal and archival sources.",
        ]),
      }),
      Object.freeze({
        version: "v3.8",
        date: "2026-05-07",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Routine monthly update."]),
      }),
    ]),
  }),
  "federal-register": Object.freeze({
    version: "v6.1",
    updated: "2026-08-04",
    cadence: CADENCE.ON_CHANGE,
    summary: "Notices through early August, with three entities matched under former names.",
    history: Object.freeze([
      Object.freeze({
        version: "v6.1",
        date: "2026-08-04",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added notices published through 1 August 2026.",
          "Matched three notices to entities appearing under former names.",
        ]),
      }),
      Object.freeze({
        version: "v6.0",
        date: "2026-07-02",
        kind: RELEASE_KIND.METHOD,
        note: "Notices naming a parent and a subsidiary are now attributed to both rather than to the parent alone.",
        changed: Object.freeze([
          "Revised attribution for notices naming more than one related entity.",
          "Reprocessed the full archive under the revised rule.",
        ]),
      }),
    ]),
  }),
  legislation: Object.freeze({
    version: "v3.4",
    updated: "2026-08-01",
    cadence: CADENCE.MONTHLY,
    summary: "July roll-call votes and newly introduced bills.",
    history: Object.freeze([
      Object.freeze({
        version: "v3.4",
        date: "2026-08-01",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added July roll-call votes and newly introduced bills.",
          "Linked nine bills to the organizations they name.",
        ]),
      }),
      Object.freeze({
        version: "v3.3",
        date: "2026-07-01",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Routine monthly update."]),
      }),
    ]),
  }),
  deals: Object.freeze({
    version: "v9.0",
    updated: "2026-07-28",
    cadence: CADENCE.CONTINUOUS,
    summary: "Twelve transactions added and three ownership relationships updated.",
    history: Object.freeze([
      Object.freeze({
        version: "v9.0",
        date: "2026-07-28",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added 12 transactions confirmed against primary sources.",
          "Updated three ownership relationships, which corrected records in Contracting and Gaming.",
        ]),
      }),
      Object.freeze({
        version: "v8.6",
        date: "2026-06-30",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Added 9 transactions and one new subsidiary."]),
      }),
    ]),
  }),
  nagpra: Object.freeze({
    version: "v2.7",
    updated: "2026-07-22",
    cadence: CADENCE.ON_CHANGE,
    summary: "New notices and inventories, matched across three decades of naming changes.",
    history: Object.freeze([
      Object.freeze({
        version: "v2.7",
        date: "2026-07-22",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added notices and inventories published since the last release.",
          "Reconciled six historical notices to their current tribal names.",
        ]),
      }),
    ]),
  }),
  lobbying: Object.freeze({
    version: "v5.2",
    updated: "2026-07-31",
    cadence: CADENCE.QUARTERLY,
    summary: "Second-quarter filings added.",
    history: Object.freeze([
      Object.freeze({
        version: "v5.2",
        date: "2026-07-31",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added Q2 2026 registrations and filings.",
          "Resolved four registrants to the tribes that retained them.",
        ]),
      }),
      Object.freeze({
        version: "v5.1",
        date: "2026-04-30",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Added Q1 2026 filings."]),
      }),
    ]),
  }),
  contractors: Object.freeze({
    version: "v6.0",
    updated: "2026-08-05",
    cadence: CADENCE.MONTHLY,
    summary: "July obligations added and 22 vendors rolled up to parent entities.",
    history: Object.freeze([
      Object.freeze({
        version: "v6.0",
        date: "2026-08-05",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added obligations reported through July 2026.",
          "Rolled 22 vendors up to their parent nation or corporation.",
          "Entity updates from the maintained identity layer affected 41 historical records.",
        ]),
      }),
      Object.freeze({
        version: "v5.4",
        date: "2026-07-06",
        kind: RELEASE_KIND.METHOD,
        note: "8(a) participation is now recorded as a status with dates rather than a fixed flag.",
        changed: Object.freeze([
          "Revised 8(a) participation to carry start and end dates.",
          "Reprocessed the archive so historical awards reflect status at the time of award.",
        ]),
      }),
    ]),
  }),
  subcontracting: Object.freeze({
    version: "v3.1",
    updated: "2026-08-05",
    cadence: CADENCE.MONTHLY,
    summary: "Subaward activity matched to the same entities as the prime awards.",
    history: Object.freeze([
      Object.freeze({
        version: "v3.1",
        date: "2026-08-05",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Added July subaward activity and matched it to the prime awards above it."]),
      }),
    ]),
  }),
  "natural-resources": Object.freeze({
    version: "v4.0",
    updated: "2026-07-15",
    cadence: CADENCE.QUARTERLY,
    summary: "Second-quarter production and disbursements.",
    history: Object.freeze([
      Object.freeze({
        version: "v4.0",
        date: "2026-07-15",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze(["Added Q2 production, royalties and disbursements."]),
      }),
    ]),
  }),
  nonprofits: Object.freeze({
    version: "v3.0",
    updated: "2026-06-25",
    cadence: CADENCE.ANNUAL,
    summary: "Native-serving classification rules revised. Read the note before reusing prior figures.",
    history: Object.freeze([
      Object.freeze({
        version: "v3.0",
        date: "2026-06-25",
        kind: RELEASE_KIND.METHOD,
        note: "Native-serving nonprofit classification rules were revised, so counts in this release are not directly comparable with v2.x.",
        changed: Object.freeze([
          "Separated Native-led from Native-serving where governance could be established from filings.",
          "Reclassified 63 organizations under the revised rules.",
          "Added the most recent filing year.",
        ]),
      }),
    ]),
  }),
  gaming: Object.freeze({
    version: "v7.3",
    updated: "2026-08-02",
    cadence: CADENCE.CONTINUOUS,
    summary: "Facility, operator and expansion activity reconciled against Deals.",
    history: Object.freeze([
      Object.freeze({
        version: "v7.3",
        date: "2026-08-02",
        kind: RELEASE_KIND.DATA,
        changed: Object.freeze([
          "Added recent expansion filings and environmental review activity.",
          "Reconciled two operator changes against Indian Country Deals.",
          "Updated employment estimates for eleven facilities.",
        ]),
      }),
    ]),
  }),
});

/** The release record for a collection, or null when it has none. */
export function releaseFor(id) {
  return PRESS_RELEASES[id] ?? null;
}

/** The most recent release entry, which is what a collection page leads with. */
export function latestRelease(id) {
  return releaseFor(id)?.history?.[0] ?? null;
}

/** Month and day, spelled the way the rest of the page spells dates. */
export function formatUpdated(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  const months = [
    "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
    "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
  ];
  return `${months[month - 1]} ${day}, ${year}`;
}

/** The short form for a metadata rail: `Updated Aug. 6 · Monthly · v4.2`. */
export function freshnessLine(id) {
  const release = releaseFor(id);
  if (!release) return "";
  const [, month, day] = release.updated.split("-").map(Number);
  const months = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
  // No version number: collections update continuously, and a vX.X on a
  // continuously maintained series read as clutter. The date is the fact.
  return `Updated ${months[month - 1]} ${day} · ${release.cadence.replace("Updated ", "")}`;
}

/**
 * The feed's activity over a trailing window: how many releases landed, how
 * many collections they touched, how many changed methodology, and the date
 * of the newest release overall.
 *
 * Computed from the release log itself, never typed into copy, so the number
 * always carries its denominator — a bare "16 releases" reads as all-time,
 * this month or the current filter, and each of those is a different claim.
 * `today` is injectable so tests do not depend on the wall clock.
 */
export function recentActivity(days = 30, today = new Date()) {
  const cutoff = today.getTime() - days * 86400000;
  const releases = Object.entries(PRESS_RELEASES).flatMap(([id, release]) =>
    release.history.map((entry) => ({ id, ...entry })),
  );
  const inWindow = releases.filter((entry) => new Date(entry.date).getTime() >= cutoff);
  const dates = releases.map((entry) => entry.date).sort();
  return {
    days,
    releases: inWindow.length,
    collections: new Set(inWindow.map((entry) => entry.id)).size,
    methodology: inWindow.filter((entry) => entry.kind === RELEASE_KIND.METHOD).length,
    latest: dates[dates.length - 1] ?? null,
  };
}

/**
 * The collections that changed most recently, newest first. Drives the
 * "recently updated" rail on the reader, which is a reason to come back.
 */
export function recentlyUpdated(limit = 3) {
  return Object.entries(PRESS_RELEASES)
    .map(([id, release]) => ({ id, ...release }))
    .sort((a, b) => (a.updated < b.updated ? 1 : -1))
    .slice(0, limit);
}
