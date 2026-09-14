// REVIEW OWNER: Havala
//
// One entity, across the collections.
//
// The record page's companion, and the reason the entity's name on a record
// is a link rather than a string. The review's distinction, 2026-09-14: a
// record page is a TRANSACTION — one funding action, one filing, one award —
// and "the entity's name should link to a separate entity profile that brings
// together its records across collections". These are the two halves of that.
//
// WHAT IT IS ALLOWED TO CLAIM
// Very little, and it says so on its face. The register gives the canonical
// name and the entity's class; the rows come from the same published ten-row
// samples every other surface reads. So the counts here are counts of PREVIEW
// records, never of the collections, and a collection showing nothing means
// the sample did not happen to include this entity — not that Cedar holds
// nothing for it. Anything stronger would need the serving layer this
// repository has not deployed, and a profile that implied it had one would be
// the most misleading page on the site.
//
// A locked collection is not read at all. The shelf is the reader's, and the
// page says how many collections it could not look in.

import { useMemo } from "react";
import { Link, useParams } from "react-router";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import {
  WITHHELD_TEXT,
  explorableCollections,
} from "../../features/grove/explore.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { recordHref } from "../../features/grove/pressRecord.js";
import { PRESS_DATA_PATH, PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useRegister } from "../../features/grove/useRegister.js";
import { useSampleRows } from "../../features/grove/useSamples.js";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function CedarPressEntity() {
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  const { uid } = useParams();
  const register = useRegister();
  useScrollToTop(uid);
  useDocumentTitle(register.byUid.get(uid)?.name ?? "Entity");

  const collections = useMemo(() => explorableCollections(user), [user]);
  // Every flagship the reader's plan opens: one dataset per collection, which
  // is what a collection is to a subscriber.
  const tables = useMemo(
    () => collections.filter((c) => c.open && c.flagship).map((c) => c.flagship),
    [collections],
  );
  const locked = collections.filter((c) => !c.open).length;
  const { rows, missing, loading: samplesLoading } = useSampleRows(tables, register);

  const entity = register.byUid.get(uid) ?? null;
  const mine = useMemo(
    () => rows.filter((item) => item.entity.entities.some((e) => e.uid === uid)),
    [rows, uid],
  );
  // Grouped by collection, in the catalog's order, so the profile reads as
  // the shelf does.
  const groups = useMemo(() => {
    const byCollection = new Map();
    for (const item of mine) {
      if (!byCollection.has(item.collection)) byCollection.set(item.collection, []);
      byCollection.get(item.collection).push(item);
    }
    return collections
      .filter((c) => byCollection.has(c.entry.id))
      .map((c) => ({ entry: c.entry, items: byCollection.get(c.entry.id) }));
  }, [mine, collections]);

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const name = entity?.withheld ? WITHHELD_TEXT : entity?.name ?? null;
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page cp-ent">
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="data" />

        <div className="cp-rec__bar">
          <Link className="cp-rec__back" to={PRESS_DATA_PATH}>
            <span aria-hidden="true">&#8592;</span> All collections
          </Link>
        </div>

        <header className="cp-rec__head" data-testid="entity-head">
          <span className="cp-rec__kind">Entity profile</span>
          <h1 className="cp-rec__name">
            {name ?? (register.entities.length ? "No entity with that Cedar id" : "Opening the entity…")}
          </h1>
          <p className="cp-rec__ids">
            <span className="cp-rec__uid">
              <code>{uid}</code>
            </span>
            {entity?.type ? <span className="cp-rec__type">{entity.type}</span> : null}
            <Link className="cp-rec__profile" to={`${PRESS_DATA_PATH}?e=${encodeURIComponent(uid)}`}>
              Open this entity in the viewer <span aria-hidden="true">&#8594;</span>
            </Link>
          </p>
          <p className="cp-rec__one">
            One identifier, held across every collection. What follows is this entity&rsquo;s records in
            the published previews — up to ten sample rows per table — and never a count of what a
            release holds.
          </p>
        </header>

        <section className="cp-ent__sum" aria-label="What the previews hold">
          <dl className="cp-rec__key">
            <div>
              <dt>Preview records</dt>
              <dd>{samplesLoading ? "…" : mine.length}</dd>
            </div>
            <div>
              <dt>Collections they sit in</dt>
              <dd>{samplesLoading ? "…" : groups.length}</dd>
            </div>
            <div>
              <dt>Collections read</dt>
              <dd>
                {tables.length}
                {locked ? <span className="cp-rec__basis">{locked} more on Cedar Press+</span> : null}
              </dd>
            </div>
          </dl>
          {missing.length ? (
            <p className="cp-rec__fine">
              Not reachable right now: {missing.map((key) => PRESS_CATALOG_BY_ID[key.split("/")[0]]?.short ?? key).join(", ")}.
            </p>
          ) : null}
        </section>

        {samplesLoading && !groups.length ? (
          <p className="cp-rec__fine cp-ent__empty">Reading the published samples…</p>
        ) : groups.length ? (
          <div className="cp-ent__groups">
            {groups.map(({ entry, items }) => (
              <section className="cp-ent__group" key={entry.id} aria-label={entry.name}>
                <header className="cp-ent__ghead">
                  <span className="cp-ent__gic" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                  <h2>{entry.name}</h2>
                  <span className="cp-ent__gn">{items.length} preview record{items.length === 1 ? "" : "s"}</span>
                </header>
                <ul className="cp-ent__list">
                  {items.map((item) => (
                    <li key={item.id}>
                      <Link className="cp-ent__row" to={recordHref({ key: item.key, recordId: item.recordId, index: item.index })}>
                        <span className="cp-ent__rowwhat">{item.observation || "—"}</span>
                        <span className="cp-ent__rowmeta">
                          {item.date ?? "undated"}
                          {item.amount != null ? ` · ${money.format(item.amount)}` : ""}
                        </span>
                        <span className="cp-ent__rowgo" aria-hidden="true">&#8594;</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        ) : (
          <p className="cp-rec__fine cp-ent__empty" data-testid="entity-empty">
            No record in the published previews names this entity. That does not establish whether
            the releases hold records for it: each table ships up to ten sample rows, and this page
            reads those.
          </p>
        )}

        <p className="cp-rec__fine cp-ent__foot">
          <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
            How a record reaches its entity <span aria-hidden="true">&#8594;</span>
          </Link>
        </p>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
