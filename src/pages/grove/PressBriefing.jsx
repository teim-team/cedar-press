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
// EVERY LINE HERE IS READ, NOT WRITTEN. The lead is the newest brief, the
// signals are the newest releases from the change ledger, the collection is
// whichever one changed most recently, and the question is scoped to it.
// Nothing on this page is copy that has to be kept in step by hand, which
// is the only way a briefing survives contact with a release schedule.
import { Link } from "react-router";

import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { PRESS_ARTICLES, articleHref } from "../../features/grove/pressArticles";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { anchorOf, formatUpdated, latestRelease, recentlyUpdated } from "../../features/grove/pressReleases";
import { PRESS_DATA_PATH, PRESS_WHATS_NEW_PATH } from "../../features/grove/pressRoutes";
import { COLLECTION_ICONS } from "./pressCollectionIcons";

/** The collection a reader should look at today: the one that just moved. */
function leadCollection() {
  const [recent] = recentlyUpdated(1);
  const id = recent?.id;
  if (!id) return null;
  const entry = PRESS_CATALOG_BY_ID[id];
  const launch = LAUNCH_COLLECTION.find((c) => c.id === id);
  return entry ? { id, entry, launch } : null;
}

export default function PressBriefing() {
  const [lead] = PRESS_ARTICLES;
  const signals = recentlyUpdated(3);
  const collection = leadCollection();
  const away = lead && !lead.hosted;

  return (
    <section className="cp-brief cp-fade" aria-label="Today's briefing">
      {/* ONE LEAD DEVELOPMENT. The newest piece of original research, at the
          size of a lead — not a card in a grid of six. */}
      {lead ? (
        <article className="cp-brief__lead">
          <span className="cp-brief__cap">The latest research</span>
          <h2 className="cp-brief__title">
            {away ? (
              <a href={articleHref(lead)} target="_blank" rel="noreferrer">
                {lead.title} <span aria-hidden="true">&#8599;</span>
              </a>
            ) : (
              <Link to={articleHref(lead)}>
                {lead.title} <span aria-hidden="true">&#8594;</span>
              </Link>
            )}
          </h2>
          <p className="cp-brief__dek">{lead.dek}</p>
          <p className="cp-brief__meta">
            {lead.date}
            {lead.datasetId && PRESS_CATALOG_BY_ID[lead.datasetId]
              ? <> · from <Link to={`${PRESS_DATA_PATH}?c=${lead.datasetId}`}>{PRESS_CATALOG_BY_ID[lead.datasetId].name}</Link></>
              : null}
            {away ? " · on Tribal Business News" : null}
          </p>
        </article>
      ) : null}

      <div className="cp-brief__side">
        {/* THREE SIGNALS. Releases, newest first, each one a link to exactly
            what changed rather than to the feed's top. */}
        <div className="cp-brief__block">
          <span className="cp-brief__cap">Worth watching</span>
          <ul className="cp-brief__signals">
            {signals.map((release) => {
              const latest = latestRelease(release.id);
              const to = latest
                ? `${PRESS_WHATS_NEW_PATH}#${anchorOf({ id: release.id, version: latest.version })}`
                : PRESS_WHATS_NEW_PATH;
              return (
                <li key={release.id}>
                  <Link to={to}>
                    <span className="cp-brief__signame">
                      {PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}
                    </span>
                    <span className="cp-brief__sigwhen">
                      {latest?.version ? `${latest.version} · ` : ""}
                      {formatUpdated(release.updated)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <Link className="cp-brief__more" to={PRESS_WHATS_NEW_PATH}>
            Every release <span aria-hidden="true">&#8594;</span>
          </Link>
        </div>

        {/* ONE COLLECTION, AND ONE QUESTION ABOUT IT. The question is scoped
            to the same collection, so pressing it asks something answerable
            rather than opening an empty box. */}
        {collection ? (
          <div className="cp-brief__block">
            <span className="cp-brief__cap">Open today</span>
            <Link className="cp-brief__coll" to={`${PRESS_DATA_PATH}?c=${collection.id}`}>
              <span className="cp-brief__collmark" aria-hidden="true">
                {COLLECTION_ICONS[collection.id] ?? null}
              </span>
              <span>
                <b>{collection.entry.name}</b>
                {collection.launch?.rowsLabel ? (
                  <small>{collection.launch.rowsLabel}</small>
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
