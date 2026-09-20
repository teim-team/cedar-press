// REVIEW OWNER: Havala
//
// The collection in hand, inside the door's product frame: what it is, how
// far back it goes, and six of its real records.
//
// THE RECORDS ARE THE PICTURE
// A marketing page stages a screenshot of the product beside its promise.
// Cedar Press has something better than a screenshot: the product is rows,
// and ten real rows of every flagship table already ship with the site
// (public/data/cedar/samples/*__10.csv), public by design — see
// pressDemoGate.js: nothing in the bundle is confidential, and the samples
// are the whole of what a visitor can reach. So the pane shows six of them,
// through the same contracts and the same row shape the viewer on /data
// uses (`universalRows`), with the caption saying exactly what they are:
// six of ten sample records, of however many the release holds. Nothing
// here is drawn for the page, and a collection with no published sample
// says so rather than borrowing a neighbour's rows.
//
// The door owns which collection is in hand; this file only draws the one
// it is given. The action names the way in at Tribal Business News for the
// shelf the collection sits on, never a route past the paywall.

import { useEffect, useMemo, useRef, useState } from "react";

import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { contractFor, exploreTables, parseCsv, universalRows } from "../../features/grove/explore.js";
import { columnPlan } from "../../features/grove/recordColumns.js";
import { Cards, Rows } from "./PressRecordTable.jsx";
import { useNarrow } from "../../features/grove/useNarrow.js";
import { coverageLabel } from "../../features/grove/pressAccess";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { freshnessLine } from "../../features/grove/pressReleases";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { TierName } from "./TierName";

/**
 * How many of the ten sample records the pane shows.
 *
 * Six, until the pane started rendering the product's own table: its rows
 * are denser than the four-column one this replaced, and six of them left a
 * third of the window empty under them. Ten is every row the sample file
 * holds, so the caption's "N of N" is the whole of what is public.
 */
const PANE_ROWS = 10;

const ROWS_LABEL = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.rowsLabel]));
const SOURCES = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.sources]));

/**
 * The sample this collection can show: `{ status, table, parsed }` where
 * status is loading, ok, failed or none. Every sample fetched is kept, so
 * moving back to a collection is instant.
 *
 * THE FLAGSHIP IS NOT ALWAYS PUBLISHED, AND THAT IS NOT AN EMPTY PAGE
 * `samples.published.json` records which declared samples are absent from
 * the repository; the Owned collection's flagship
 * (native_owned_businesses.csv) is one of them today, reason "not in
 * repository". The release still publishes a supporting table, so the pane
 * shows that rather than an empty state, and says which it is. Falling back
 * is honest because the caption names the table either way; what would not
 * be honest is a pane implying the flagship is what a reader is seeing, so
 * `table.flagship` travels with it and the caption reads off it.
 */
function usePreviewSample(collectionId) {
  const [loaded, setLoaded] = useState(() => new Map());
  const pending = useRef(new Set());
  const table = useMemo(() => {
    const tables = exploreTables(collectionId);
    const flagship = tables.find((t) => t.flagship);
    if (flagship) return flagship;
    // A supporting table stands in only if its contract names the entity
    // each row belongs to. The Owned collection's published supporting
    // table declares no entity and no date, so standing it up here filled
    // the door with six rows reading "not linked to an entity" — true of
    // that table, and a lie about the collection. Better to say the
    // preview is pending and show what the release holds.
    return tables.find((t) => contractFor(t.key)?.entity_name || contractFor(t.key)?.entity_uid) ?? null;
  }, [collectionId]);
  useEffect(() => {
    if (!table || loaded.has(table.path) || pending.current.has(table.path)) return;
    pending.current.add(table.path);
    fetch(table.path)
      .then(async (r) => (r.ok ? parseCsv(await r.text()) : null))
      .catch(() => null)
      .then((parsed) => {
        pending.current.delete(table.path);
        setLoaded((prev) => (prev.has(table.path) ? prev : new Map(prev).set(table.path, parsed)));
      });
  }, [table, loaded]);
  if (!table) return { status: "none", table: null, parsed: null };
  if (!loaded.has(table.path)) return { status: "loading", table, parsed: null };
  const parsed = loaded.get(table.path);
  return { status: parsed ? "ok" : "failed", table, parsed };
}

export default function CollectionPreview({ entry, tier, register }) {
  const { status, table, parsed } = usePreviewSample(entry.id);
  // A phone gets the same list the product gives a phone, not a table of
  // the collection's own columns squeezed into 320px.
  const narrow = useNarrow();
  const items = useMemo(
    () => (parsed ? universalRows(table.key, parsed.rows, register).slice(0, PANE_ROWS) : []),
    [parsed, table, register],
  );
  const showAmount = items.some((item) => item.amount != null);
  // The columns the product would open this collection on, off the same
  // contract and the same plan. The sample file's own header is the column
  // universe here, exactly as the release's is on /data.
  const contract = table ? contractFor(table.key) : null;
  const entityColumn = contract ? (contract.entity_name ?? contract.entity_uid ?? null) : null;
  const { defaults, all } = columnPlan(table?.key ?? null, contract, parsed?.columns ?? []);
  const shownColumns = defaults.length ? defaults : all;
  const rowsLabel = ROWS_LABEL[entry.id];
  const fresh = freshnessLine(entry.id);
  return (
    <div className="cp-pane" data-testid="collection-stage" data-collection={entry.id}>
      <div className="cp-pane__head">
        <div className="cp-pane__id">
          <span className="cp-pane__cap">Included in <TierName name={tier.name} /></span>
          <h3 className="cp-pane__name"><TierName name={entry.name} /></h3>
        </div>
        <p className="cp-pane__facts">
          <span>{coverageLabel(entry)}</span>
          {rowsLabel ? <span>{rowsLabel}</span> : null}
          {fresh ? <span>{fresh}</span> : null}
        </p>
        <p className="cp-pane__blurb">{entry.blurb}</p>
      </div>

      {status === "ok" && items.length ? (
        <>
          <p className="cp-pane__tablecap">
            <span>
              {table.table.replace(/_/g, " ")}
              {table.flagship ? null : <em> · supporting table</em>}
            </span>
            <span>
              {items.length} of {parsed.rows.length} sample records
              {table.rows ? ` · ${table.rows.toLocaleString("en-US")} in the release` : ""}
            </span>
          </p>
          {/* THE SAME TABLE, NOT A TABLE THAT LOOKS LIKE IT.
              This pane drew four columns of its own naming — Entity, Date,
              Record, Amount — while the product opened on the collection's
              own fields behind a pinned Cedar identity block. A visitor was
              being shown a picture of a product they would not recognise on
              the first day. It renders `Rows` now: the same component, the
              same `columnPlan`, the same cell rules, read-only. */}
          <div className="cp-pane__records">
            {narrow ? (
              <Cards readOnly items={items} onActive={() => {}} openRecord={null} />
            ) : (
            <Rows
              readOnly
              view="table"
              items={items}
              columns={shownColumns}
              sort={null}
              onSort={() => {}}
              onActive={() => {}}
              showAmount={showAmount}
              entityColumn={entityColumn}
              contract={contract}
              openRecord={null}
            />
            )}
          </div>
        </>
      ) : status === "loading" ? (
        <p className="cp-pane__empty" aria-busy="true">Reading the sample…</p>
      ) : (
        <div className="cp-pane__pending">
          <span className="cp-pane__pendingcap">
            {status === "none" ? "Preview pending" : "The sample could not be read"}
          </span>
          {status === "none" ? (
            <p>
              The ten-row sample of this collection&rsquo;s main table was produced with the
              current release and is not on the site yet, so there is nothing here to show you
              that would be real. The release itself ships {rowsLabel ? <b>{rowsLabel}</b> : "in full"}.
            </p>
          ) : (
            <p>The sample file did not load. The release is unaffected.</p>
          )}
          {SOURCES[entry.id] ? (
            <p className="cp-pane__sources">
              <span className="cp-pane__sourcecap">Built from</span>
              {SOURCES[entry.id]}
            </p>
          ) : null}
        </div>
      )}

      {/* No linkage sentence here: the owner took the entity-linkage claim
          off the door on 2026-09-04, and it still lives on /data. */}
      {status === "ok" && table && !table.flagship ? (
        <p className="cp-pane__note">
          This collection&rsquo;s main table ships with the release; its sample is not published
          on the site yet, so the preview shows a supporting table from the same release.
        </p>
      ) : null}
      <div className="cp-pane__foot">
        <p className="cp-pane__acts">
          <a
            className="cp-pane__act"
            href={TBN_PLANS_URL}
            target="_blank"
            rel="noreferrer"
            onClick={() => track(EVENT.upgradeOpened, { collection: entry.id, shelf: entry.shelf })}
          >
            Get <TierName name={tier.name} /> <span aria-hidden="true">&#8594;</span>
          </a>
          <button
            type="button"
            className="cp-pane__act cp-pane__act--btn"
            onClick={() =>
              window.dispatchEvent(
                new CustomEvent("cedar:ask-collection", { detail: { id: entry.id, name: entry.name } }),
              )
            }
          >
            Ask Cedar <span aria-hidden="true">&#8594;</span>
          </button>
        </p>
      </div>
    </div>
  );
}
