// REVIEW OWNER: Havala
//
// The front page's collections: every collection on its shelf, and beside
// the list a stage showing the one in hand.
//
// THE RECORDS ARE THE PICTURE
// A marketing page stages a screenshot of the product beside its promise.
// This page has something better than a screenshot: the product is rows,
// and ten real rows of every flagship table already ship with the site
// (public/data/cedar/samples/*__10.csv). So the stage shows six of them,
// through the same contract and the same row shape the viewer on /data
// uses (`universalRows`), with the caption saying exactly what they are —
// six of ten sample records, of however many the release holds. Nothing
// here is drawn for the page.
//
// LIST AND STAGE, NOT A GRID OF SQUARES
// The shelf on /data lays its collections out as square badges with a
// reader beside them; the reader held prose, and a square cannot say what
// a collection is. Here the collections are a list down the left, grouped
// by shelf, and the stage on the right carries the description and the
// records. Clicking a row selects it; hovering changes nothing, so the
// records under the cursor never move while it travels to the actions.
//
// LOCKED COLLECTIONS STAY LISTED AND STAY PREVIEWED
// The viewer already shows a locked collection's sample to a reader
// deciding whether to upgrade (`explorableCollections`), so the stage does
// the same. Only the actions differ: an open collection browses and
// downloads, a locked one names what opens it.
//
// ON A PHONE THE STAGE FOLLOWS THE ROW
// Below 720px the stage renders inside the selected row rather than in a
// column that would sit under the whole list, a screen away from the tap
// that opened it.

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";

import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import {
  EMPTY_CUT,
  EMPTY_REGISTER,
  WITHHELD_TEXT,
  buildRegister,
  encodeCut,
  exploreTables,
  parseCsv,
  universalRows,
} from "../../features/grove/explore.js";
import { canOpenDataset, coverageLabel } from "../../features/grove/pressAccess";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { PRESS_TIERS, collectionsOnShelf } from "../../features/grove/pressCatalog";
import { freshnessLine } from "../../features/grove/pressReleases";
import { PRESS_DATA_PATH } from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { useNarrow } from "../../features/grove/useNarrow.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { TierName } from "./TierName";

const REGISTER_PATH = "/data/cedar/register.json";
/** How many of the ten sample records the stage shows. Six fits a screen
 *  beside the description without the stage becoming the viewer. */
export const STAGE_ROWS = 6;

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const ROWS_LABEL = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.rowsLabel]));

/** The register, or the empty one: a row still names its entity from its
 *  own columns when the register cannot be read, so the stage degrades to
 *  names without types rather than to nothing. */
function useRegister() {
  const [register, setRegister] = useState(EMPTY_REGISTER);
  useEffect(() => {
    let live = true;
    fetch(REGISTER_PATH)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json) => { if (live) setRegister(buildRegister(json)); })
      .catch(() => {});
    return () => { live = false; };
  }, []);
  return register;
}

/**
 * The flagship sample for a collection: `{ status, table, parsed }` where
 * status is loading, ok, failed or none (no published sample). Every
 * sample fetched is kept, so moving back to a collection is instant.
 */
function useFlagshipSample(collectionId) {
  const [loaded, setLoaded] = useState(() => new Map());
  const pending = useRef(new Set());
  const table = useMemo(() => exploreTables(collectionId).find((t) => t.flagship) ?? null, [collectionId]);
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

/** The short coverage note beside a name in the list. */
function coverageShort(entry) {
  const coverage = entry.coverage;
  if (coverage?.kind === "series" && coverage.from) return `since ${coverage.from}`;
  if (coverage?.kind === "roster") return "current roster";
  return "";
}

function Stage({ entry, tier, owned, register }) {
  const { status, table, parsed } = useFlagshipSample(entry.id);
  const items = useMemo(
    () => (parsed ? universalRows(table.key, parsed.rows, register).slice(0, STAGE_ROWS) : []),
    [parsed, table, register],
  );
  const showAmount = items.some((item) => item.amount != null);
  const rowsLabel = ROWS_LABEL[entry.id];
  const fresh = freshnessLine(entry.id);
  // The viewer on /data, already on this collection.
  const browse = `${PRESS_DATA_PATH}?${encodeCut({ ...EMPTY_CUT, collections: [entry.id] })}`;
  return (
    <div className="cp-stage" data-testid="collection-stage" data-collection={entry.id}>
      <div className="cp-stage__head">
        <span className="cp-read__cap">
          {owned ? "Your collection" : <>In <TierName name={tier.name} /></>}
        </span>
        <h3 className="cp-stage__name"><TierName name={entry.name} /></h3>
        <p className="cp-stage__blurb">{entry.blurb}</p>
        {entry.linkage ? (
          <p className="cp-stage__link">
            <span className="cp-read__linkcap">What Cedar adds</span>
            {entry.linkage}
          </p>
        ) : null}
        <p className="cp-stage__facts">
          <span>{coverageLabel(entry)}</span>
          {rowsLabel ? <span>{rowsLabel}</span> : null}
          {fresh ? <span>{fresh}</span> : null}
        </p>
      </div>

      {status === "ok" && items.length ? (
        <>
          <p className="cp-stage__cap">
            <span>{table.table.replace(/_/g, " ")}</span>
            <span>
              {items.length} of {parsed.rows.length} sample records
              {table.rows ? ` · ${table.rows.toLocaleString("en-US")} in the release` : ""}
            </span>
          </p>
          <div className="cp-stage__scroll">
            <table className="cp-stage__table">
              <thead>
                <tr>
                  <th scope="col">Entity</th>
                  <th scope="col">Date</th>
                  <th scope="col">Record</th>
                  {showAmount ? <th scope="col" className="cp-stage__amt">Amount</th> : null}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} data-testid="stage-record">
                    <td className="cp-stage__ent">
                      {item.entity.withheld ? <em>{WITHHELD_TEXT}</em> : item.entity.name ?? <span className="cp-stage__unkeyed">not linked to an entity</span>}
                      {item.entity.uid ? <small className="cp-stage__uid">{item.entity.uid}</small> : null}
                    </td>
                    <td className="cp-stage__date">{item.date ?? "—"}</td>
                    <td className="cp-stage__obs"><span className="cp-stage__clamp">{item.observation || item.subject || "—"}</span></td>
                    {showAmount ? (
                      <td className="cp-stage__amt">
                        {item.amount == null ? "—" : money.format(item.amount)}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : status === "loading" ? (
        <p className="cp-stage__empty" aria-busy="true">Reading the sample…</p>
      ) : (
        // Failed, or no sample is published: said, not padded. A stage that
        // borrowed another collection's rows would be the page lying about
        // what this one holds.
        <p className="cp-stage__empty">
          {status === "none" ? "No preview is published for this collection yet." : "The sample could not be read."}
        </p>
      )}

      <p className="cp-stage__acts">
        {owned ? (
          <Link
            className="cp-stage__act"
            to={browse}
            onClick={() => track(EVENT.collectionViewed, { collection: entry.id, shelf: entry.shelf })}
          >
            Browse the records <span aria-hidden="true">&#8594;</span>
          </Link>
        ) : (
          <a
            className="cp-stage__act"
            href={TBN_PLANS_URL}
            target="_blank"
            rel="noreferrer"
            onClick={() => track(EVENT.upgradeOpened, { collection: entry.id, shelf: entry.shelf })}
          >
            Get <TierName name={tier.name} /> at Tribal Business News <span aria-hidden="true">&#8594;</span>
          </a>
        )}
        <button
          type="button"
          className="cp-stage__act cp-stage__act--btn"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("cedar:ask-collection", { detail: { id: entry.id, name: entry.name } }),
            )
          }
        >
          Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
        </button>
      </p>
    </div>
  );
}

export default function PressCollectionsStage({ user }) {
  const shelves = PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => ({
    tier,
    owned: canOpenDataset(user, { shelf: tier.shelf }),
    entries: collectionsOnShelf(tier.shelf),
  }));
  const all = shelves.flatMap((shelf) => shelf.entries.map((entry) => ({ entry, tier: shelf.tier, owned: shelf.owned })));
  // First open collection in shelf order, else the first there is: the
  // stage is never empty on arrival.
  const [selectedId, setSelectedId] = useState(() => (all.find((item) => item.owned) ?? all[0])?.entry.id ?? null);
  const selected = all.find((item) => item.entry.id === selectedId) ?? null;
  const register = useRegister();
  const narrow = useNarrow();

  const pick = (item) => {
    setSelectedId(item.entry.id);
    track(EVENT.sectionOpened, { section: "collections", collection: item.entry.id });
  };

  const stage = selected ? (
    <Stage key={selected.entry.id} entry={selected.entry} tier={selected.tier} owned={selected.owned} register={register} />
  ) : null;

  return (
    <section className="cp-shelves cp-fade" aria-label="The collections">
      <div className="cp-shelf">
        {shelves.map(({ tier, owned, entries }) => (
          <div className="cp-shelf__tier" key={tier.id}>
            <span className="cp-shelf__eyebrow">
              <TierName name={tier.name} /> · {owned ? "Your shelf" : "Locked"}
            </span>
            <p className="cp-shelf__q">{tier.question}</p>
            <ul className="cp-shelf__list">
              {entries.map((entry) => {
                const item = { entry, tier, owned };
                const on = entry.id === selectedId;
                return (
                  <li key={entry.id} className={`cp-shelf__item${on ? " is-on" : ""}${owned ? "" : " is-locked"}`}>
                    <button type="button" className="cp-shelf__pick" aria-pressed={on} onClick={() => pick(item)}>
                      <span className="cp-shelf__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
                      <span className="cp-shelf__id">
                        <span className="cp-shelf__name"><TierName name={entry.short || entry.name} /></span>
                        <span className="cp-shelf__meta">
                          {[coverageShort(entry), ROWS_LABEL[entry.id]].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                      <span className="cp-shelf__cue" aria-hidden="true">{owned ? "→" : "+"}</span>
                    </button>
                    {narrow && on ? stage : null}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      {narrow ? null : <div className="cp-shelves__stage">{stage}</div>}
    </section>
  );
}
