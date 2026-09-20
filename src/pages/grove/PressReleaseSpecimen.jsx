// The release specimen: a small piece of real bookkeeping in the hero.
//
// The door's upper-right was a dead zone — a headline on the left, a product
// frame below, and a column of nothing between them. The temptation there is
// a metric card or a pattern, and the brief rules both out: "Do not fill it
// with generic metric cards, a decorative pattern, another paragraph, or a
// second chatbot."
//
// So it holds the one thing the page is otherwise only asserting: that these
// collections are MAINTAINED. A version, a date, and the release's own
// counts. Every figure comes from `collections.manifest.json` by way of
// `collection.js` — nothing here is written, and nothing is a delta, because
// the manifest records the current release and not the one before it. The
// brief is explicit about that too: "never invent added-record counts."
//
// It is the selected collection's, so pointing at the rail below changes it
// and the two objects read as one surface rather than as a card beside a
// screenshot.
import { LAUNCH_COLLECTION, collectionCedarFacts } from "../../features/grove/collection";
import { coverageLabel } from "../../features/grove/pressAccess";
import { formatUpdated } from "../../features/grove/pressReleases";
import { COLLECTION_ICONS } from "./pressCollectionIcons";

/** "3646750" as the release states it, or null rather than a guess. */
function rowsOf(entry, facts) {
  if (entry?.rowsLabel) return entry.rowsLabel;
  return Number.isInteger(facts?.n_rows) ? `${facts.n_rows.toLocaleString("en-US")} rows` : null;
}

/** The release descriptors, by id: the catalog entry does not carry them. */
const RELEASE = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry]));

export default function PressReleaseSpecimen({ entry }) {
  if (!entry) return null;
  const facts = collectionCedarFacts(entry.id);
  // The version and the date live on the LAUNCH descriptor, not on the
  // storefront catalog entry this component is handed. Reading them off
  // `entry` rendered a specimen with a table count and no release, which is
  // the one thing it exists to state.
  const release = RELEASE[entry.id] ?? {};
  const rows = rowsOf(release, facts);
  const tables = Number.isInteger(facts?.n_tables) ? facts.n_tables : null;
  const coverage = coverageLabel(entry);

  return (
    <aside className="cp-spec cp-fade" aria-label="Current release">
      <p className="cp-spec__cap">
        Cedar Press <span aria-hidden="true">/</span> Current release
      </p>
      <p className="cp-spec__name">
        <span className="cp-spec__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
        {entry.name}
      </p>
      {coverage ? <p className="cp-spec__cover">{coverage}</p> : null}
      {/* The bookkeeping, as fields rather than as a sentence: a reader
          checking whether a release is current reads a date, not prose. */}
      <dl className="cp-spec__facts">
        {release.version ? (
          <div>
            <dt>Release</dt>
            <dd>{release.version}</dd>
          </div>
        ) : null}
        {release.updated ? (
          <div>
            <dt>Updated</dt>
            <dd>{formatUpdated(release.updated)}</dd>
          </div>
        ) : null}
        {tables ? (
          <div>
            <dt>Tables</dt>
            <dd>{tables}</dd>
          </div>
        ) : null}
      </dl>
      {rows ? <p className="cp-spec__rows">{rows}</p> : null}
    </aside>
  );
}
