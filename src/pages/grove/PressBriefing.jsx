// REVIEW OWNER: Havala
//
// THE FRONT PAGE IS A BRIEFING, NOT A MENU.
//
// Owner, 2026-09-20: "'Know what's shaping Indian Country' is a good
// premise, but the current page is a lightly branded dashboard with several
// dense blocks. Make it feel more like a briefing: one lead development,
// three signals worth watching, one collection or research brief to explore,
// one Cedar question worth asking."
//
// What it replaced: six cards reading Collections, Research Briefs,
// Priorities, What's new, Methods and Plans — the navigation bar, restated
// underneath itself as tiles. A reader who is already signed in does not
// need the product's table of contents twice; they need to know what moved.
//
// The redesign took the lead research brief off it: the page is the
// collections and what moved in them.
//
// EVERY LINE HERE IS READ, NOT WRITTEN. The signals are the newest releases
// from the change ledger, the collection is
// whichever one changed most recently, and the question is scoped to it.
// Nothing on this page is copy that has to be kept in step by hand, which
// is the only way a briefing survives contact with a release schedule.
import { Link } from "react-router";

import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import { PRESS_DATA_PATH } from "../../features/grove/pressRoutes";
import { COLLECTION_ICONS } from "./pressCollectionIcons";

/** The collection a reader should look at today: the one that just moved. */
function leadCollection(releases) {
  const [recent] = recentlyUpdated(1, releases);
  const id = recent?.id;
  if (!id) return null;
  const entry = PRESS_CATALOG_BY_ID[id];
  return entry ? { id, entry, count: recent.record_count } : null;
}

export default function PressBriefing({ releaseState }) {
  const releases = releaseState?.data?.releases ?? {};
  const signals = recentlyUpdated(3, releases);
  const collection = leadCollection(releases);

  return (
    <section className="cp-brief cp-fade" aria-label="Today's briefing">
      <div className="cp-brief__side">
        {/* THREE SIGNALS. Releases, newest first, each one a link to the
            collection that changed. */}
        <div className="cp-brief__block">
          <span className="cp-brief__cap">{releaseState?.data?.source === "verified_current" ? "Available now" : "Updates"}</span>
          {!releaseState?.data ? <p role="status">{releaseState?.status === "loading" ? "Loading collection updates…" : "Collection updates are unavailable."}</p> : null}
          <ul className="cp-brief__signals">
            {signals.map((release) => (
                <li key={release.id}>
                  <Link to={`${PRESS_DATA_PATH}?c=${release.id}`}>
                    <span className="cp-brief__signame">
                      {PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}
                    </span>
                    <span className="cp-brief__sigwhen">
                      {release.updated ? formatUpdated(release.updated) : "Current verified data"}
                    </span>
                  </Link>
                </li>
            ))}
          </ul>
          <Link className="cp-brief__more" to={PRESS_DATA_PATH}>
            All collections <span aria-hidden="true">&#8594;</span>
          </Link>
        </div>

        {/* ONE COLLECTION, AND ONE QUESTION ABOUT IT. The question is scoped
            to the same collection, so pressing it asks something answerable
            rather than opening an empty box. */}
        {collection ? (
          <div className="cp-brief__block">
            <span className="cp-brief__cap">Explore the records</span>
            <Link className="cp-brief__coll" to={`${PRESS_DATA_PATH}?c=${collection.id}`}>
              <span className="cp-brief__collmark" aria-hidden="true">
                {COLLECTION_ICONS[collection.id] ?? null}
              </span>
              <span>
                <b>{collection.entry.name}</b>
                {Number.isSafeInteger(collection.count) ? (
                  <small>{collection.count.toLocaleString()} available observations</small>
                ) : null}
              </span>
            </Link>
            <button
              type="button"
              className="cp-brief__ask"
              onClick={() =>
                window.dispatchEvent(
                  new CustomEvent("cedar:ask-collection", {
                    detail: {
                      id: collection.id,
                      name: collection.entry.name,
                      q: `What changed in ${collection.entry.name}?`,
                    },
                  }),
                )
              }
            >
              Ask Cedar what changed in it <span aria-hidden="true">&#8594;</span>
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
