// REVIEW OWNER: Havala
//
// The collections, on the door: every collection on its shelf, and beside
// the list a stage showing the one in hand.
//
// THE RECORDS ARE THE PICTURE
// A marketing page stages a screenshot of the product beside its promise.
// Cedar Press has something better than a screenshot: the product is rows,
// and ten real rows of every flagship table already ship with the site
// (public/data/cedar/samples/*__10.csv), public by design — see
// pressDemoGate.js: nothing in the bundle is confidential, and the samples
// are the whole of what a visitor can reach. So the stage shows six of
// them, through the same contracts and the same row shape the viewer on
// /data uses (`universalRows`), with the caption saying exactly what they
// are: six of ten sample records, of however many the release holds.
// Nothing here is drawn for the page, and a collection with no published
// sample says so rather than borrowing a neighbour's rows.
//
// LIST AND STAGE, NOT A GRID OF SQUARES
// The collections are a list down the left, grouped by shelf, and the
// stage on the right carries the description and the records. Clicking a
// row selects it; hovering changes nothing, so the records under the cursor
// never move while it travels to the actions.
//
// WHO IS LOOKING
// `visitor` is the door: nobody is signed in, both shelves are for sale,
// and the stage's action is the way to buy the shelf the collection sits
// on. Without it the stage reads the reader's entitlement, opens what they
// own in the viewer and names the upgrade for what they do not.
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

function Stage({ entry, tier, owned, visitor, register }) {
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
          {visitor ? <>Included in <TierName name={tier.name} /></> : owned ? "Your collection" : <>In <TierName name={tier.name} /></>}
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
        <p className="cp-stage__empty">
          {status === "none" ? "No preview is published for this collection yet." : "The sample could not be read."}
        </p>
      )}

      <p className="cp-stage__acts">
        {!visitor && owned ? (
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

export default function PressCollectionsStage({ user = null, visitor = false }) {
  const shelves = PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => ({
    tier,
    owned: !visitor && canOpenDataset(user, { shelf: tier.shelf }),
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
    <Stage key={selected.entry.id} entry={selected.entry} tier={selected.tier} owned={selected.owned} visitor={visitor} register={register} />
  ) : null;

  return (
    <div className="cp-shelves">
      <div className="cp-shelf">
        {shelves.map(({ tier, owned, entries }) => (
          <div className="cp-shelf__tier" key={tier.id}>
            <span className="cp-shelf__eyebrow">
              <TierName name={tier.name} /> · {visitor ? `${entries.length} collections` : owned ? "Your shelf" : "Locked"}
            </span>
            <p className="cp-shelf__q">{tier.question}</p>
            <ul className="cp-shelf__list">
              {entries.map((entry) => {
                const item = { entry, tier, owned };
                const on = entry.id === selectedId;
                return (
                  <li key={entry.id} className={`cp-shelf__item${on ? " is-on" : ""}`}>
                    <button type="button" className="cp-shelf__pick" aria-pressed={on} onClick={() => pick(item)}>
                      <span className="cp-shelf__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
                      <span className="cp-shelf__id">
                        <span className="cp-shelf__name"><TierName name={entry.short || entry.name} /></span>
                        <span className="cp-shelf__meta">
                          {[coverageShort(entry), ROWS_LABEL[entry.id]].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                      <span className="cp-shelf__cue" aria-hidden="true">&#8594;</span>
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
    </div>
  );
}
