// REVIEW OWNER: Havala
//
// The shelves.
//
// One full-bleed band per tier, alternating filled and plain, so the tiers
// are what divide the page.
//
// A band is two halves. On the left the tier says what it is and lays out its
// collections as square badges. On the right, the space beside them is the
// reader: hover or focus a badge and it tells you what that collection is,
// how far back it goes and whether you can take it right now. That space used
// to be empty, and a square cannot say what a collection is without turning
// back into the card this replaced.
//
// A badge is the download. Click it and you get the file, with no second
// step, no detail page and no button drawn on top of it. A locked badge
// clicks too: it walks you to the panel that says what opens it. What's New
// is the one page that tracks changes; the per-collection pages are gone.
//
// THE TWO SHELVES INVERT
// Cedar Press sits on teal with white tiles and teal marks; Cedar Press+ sits
// on white with teal tiles and white marks. Same two colours both times,
// swapped, which is what makes them read as one set rather than as an
// available thing and a greyed-out thing. A locked tile looks like its
// shelf; the band's own eyebrow and the reader panel carry the lock.
//
// Tiles lay out in balanced rows, not as many as the width allows: the column
// count comes from the entry count (`--cols`), so six read as three and three
// and four as two and two.
//
// FILTERED TO DATA, THIS IS THE READER'S OWN SHELF
// No locked band and no Cedar Grove. Somebody who asked to see the
// collections asked for the ones they can open, and answering with an upsell
// answers a different question. Everything else still shows both.
//
// The lock is a client-side affordance. `pressAccess` says so in its own
// header; the server has to answer identically before real data sits behind
// any of this.

import { useEffect, useRef, useState } from "react";

// Whether this device points with a finger: no hover means the point-to-read
// affordance below becomes tap-to-read, and a tile's download moves one tap
// further so nobody takes a file before reading what it is.
const COARSE = typeof window !== "undefined" && !!window.matchMedia?.("(hover: none)").matches;

import { appUrl } from "../../features/grove/appLink.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { canOpenDataset, historyFor } from "../../features/grove/pressAccess";
import { downloadAll, downloadCsv, hasReleaseFile } from "../../features/grove/pressDownload";
import {
  GROVE_CAPABILITIES,
  PRESS_CATALOG_BY_ID,
  PRESS_TIERS,
  collectionsOnShelf,
} from "../../features/grove/pressCatalog";
import { freshnessLine } from "../../features/grove/pressReleases";
import { TBN_URL } from "../../features/grove/pressArticles";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { TierName } from "./TierName";

/**
 * Cedar Grove is not a fourth shelf holding one collection. It carries
 * everything Cedar Press does, its own exclusives, and the harmonized public
 * data, so its band shows all of that rather than the single badge that made
 * the tier look smaller than the two above it.
 */


/**
 * Marks the band once it has been scrolled to, so the badges can arrive
 * rather than being there already. One-way: a band that has been seen stays
 * seen, because re-animating on the way back up is the thing that makes a
 * page feel restless.
 */
function useReveal() {
  const ref = useRef(null);
  // Anywhere without IntersectionObserver starts revealed, decided at mount
  // rather than corrected by an effect: a band that flashes in on a browser
  // that cannot observe it is worse than one that was simply always there.
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === "undefined");
  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { rootMargin: "-8% 0px -8% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [seen]);
  return [ref, seen];
}

function Badge({ entry, open, onEnter, active, index, onLocked, onOpen }) {
  const className = `cp-badge${active ? " is-on" : ""}${open ? " cp-badge--act" : " cp-badge--locked"}`;
  // The selection is sticky on every pointer, not only touch: the read panel
  // carries its own actions (Ask Cedar, the touch download), and clearing on
  // mouse-leave or blur unmounted those buttons under the very pointer
  // traveling to click them. The panel changes when another tile is pointed
  // at, never back to the idle hint.
  const watch = { onMouseEnter: onEnter, onFocus: onEnter };
  const inner = (
    <>
      <span className="cp-badge__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
      <span className="cp-badge__name"><TierName name={entry.short || entry.name} /></span>
    </>
  );
  // The badges arrive in sequence rather than all at once, which is what
  // makes a grid read as a shelf filling up instead of a page repainting.
  const style = { "--i": index };

  // Every tile answers a click on both shelves, and the cue says what the
  // answer is: an owned tile hands over the file (the down arrow is the
  // download), a locked one walks you to what opens it. Only the symbol
  // differs, so the two shelves keep one hover language.
  if (!open) {
    return (
      <li style={style}>
        <button type="button" className={className} onClick={onLocked} {...watch}>
          {inner}
          <span className="cp-badge__cue" aria-hidden="true">&#8594;</span>
          <span className="cp-badge__sr">See what opens {entry.name}</span>
        </button>
      </li>
    );
  }
  // A tile without a release extract must not promise one: what it hands
  // over is a description of the collection, and the label says so until the
  // real release bundle exists.
  const released = hasReleaseFile(entry);
  return (
    <li style={style}>
      <button type="button" className={className} onClick={() => onOpen(entry)} {...watch}>
        {inner}
        <span className="cp-badge__cue" aria-hidden="true">&#8595;</span>
        <span className="cp-badge__sr">
          {released
            ? `Download ${entry.name}`
            : `Download the ${entry.name} collection description; the release file is pending`}
        </span>
      </button>
    </li>
  );
}

/**
 * Coverage, said the way this reader actually receives it.
 *
 * A Cedar Press reader was being shown the full archive start, which
 * describes a series nobody sold them. Where the two differ, both are
 * named, without naming a tier: the band above already says which one this
 * is.
 */
function coverageLine(entry, user, owned) {
  const history = historyFor(user, entry);
  const standard = history.standard ?? entry.standardFrom;
  const full = history.full ?? entry.historyFrom;
  if (!standard) return "Coverage varies";
  if (owned && history.from && history.from < standard) return `${history.from} to present`;
  if (full != null && full < standard) return `${standard} to present · full archive from ${full}`;
  return `${standard} to present`;
}

/** Whether Cedar has a profile to answer from for this collection. Every
 *  catalog collection has one now: the launch four answer from their releases
 *  and the rest from their catalog entries (collection_profiles.py), so only
 *  an entry outside the catalog — the harmonized public data — goes without
 *  the button. */
function hasCedarProfile(id) {
  return Boolean(PRESS_CATALOG_BY_ID[id]) || LAUNCH_COLLECTION.some((d) => d.id === id);
}

/** What the reader says about the collection under the cursor. */
function Detail({ entry, user, owned }) {
  return (
    <div className="cp-read__on">
      <span className="cp-read__cap">
        {entry.kind === "public" ? "Harmonized public data" : "Cedar collection"}
      </span>
      <h4 className="cp-read__name"><TierName name={entry.name} /></h4>
      <p className="cp-read__blurb">{entry.blurb}</p>
      {entry.linkage ? (
        <p className="cp-read__link">
          <span className="cp-read__linkcap">The link</span>
          {entry.linkage}
        </p>
      ) : null}
      <p className="cp-read__foot">
        {coverageLine(entry, user, owned)}
        {" · "}
        {freshnessLine(entry.id) ||
          (owned
            ? hasReleaseFile(entry)
              ? COARSE ? "Tap to download" : "Click to download"
              : `Release pending; ${COARSE ? "tap" : "click"} for the collection description`
            : "Locked")}
      </p>
      {/* On touch the tile's first tap lands here, so the panel carries the
          action itself rather than sending the finger back to the grid. */}
      {COARSE && owned ? (
        <button type="button" className="cp-read__act" onClick={() => downloadCsv(entry)}>
          <span aria-hidden="true">&#8595;</span>{" "}
          {hasReleaseFile(entry) ? `Download ${entry.short || entry.name}` : "Download the description"}
        </button>
      ) : null}
      {/* Cedar, already scoped: the reader looking at this description is
          one click from asking how the collection was built or what its
          headline figures are, without restating which collection. The
          event reaches the floating control without a prop path. */}
      {hasCedarProfile(entry.id) ? (
        <button
          type="button"
          className="cp-read__cedar"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("cedar:ask-collection", {
                detail: { id: entry.id, name: entry.name },
              }),
            )
          }
        >
          Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
        </button>
      ) : null}
    </div>
  );
}


function Band({ tier, user, index }) {
  const entries = collectionsOnShelf(tier.shelf);
  const [hovered, setHovered] = useState(null);

  // Off the tier's own shelf, never off its first entry: Grove's band leads
  // with the collections Cedar Press also carries, so asking about entry
  // zero told a Cedar Press reader that Cedar Grove was their shelf.
  const owned = canOpenDataset(user, { shelf: tier.shelf });
  const starts = entries
    .map((entry) => historyFor(user, entry))
    .map((history) => (owned ? history.from : history.full))
    .filter(Boolean);
  const from = starts.length ? Math.min(...starts) : null;
  const active = entries.find((entry) => entry.id === hovered) || null;
  const [ref, seen] = useReveal();

  // A locked tile's click walks the reader to the answer: the panel that
  // says what the collection is and carries the way in. The ring is so the
  // eye lands there even when the panel was already on screen.
  const readRef = useRef(null);
  const [pulse, setPulse] = useState(false);
  const pointAtUpgrade = () => {
    track(EVENT.lockedCollectionTapped, { shelf: tier.shelf });
    readRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setPulse(true);
    window.setTimeout(() => setPulse(false), 900);
  };

  // On a coarse pointer the first tap reads, the second (or the panel's own
  // button) downloads: hover cannot introduce the collection first, so the
  // tap that would have done both walks the reader to the panel instead.
  const [armed, setArmed] = useState(null);
  const openTile = (entry) => {
    track(EVENT.collectionViewed, { collection: entry.id, shelf: tier.shelf });
    if (COARSE && armed !== entry.id) {
      setArmed(entry.id);
      setHovered(entry.id);
      readRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      setPulse(true);
      window.setTimeout(() => setPulse(false), 900);
      return;
    }
    track(EVENT.collectionDownloaded, { collection: entry.id, shelf: tier.shelf });
    downloadCsv(entry);
  };

  return (
    <section
      ref={ref}
      className={`cp-band cp-band--${index % 2 === 0 ? "fill" : "plain"}${seen ? " is-in" : ""}`}
      aria-label={tier.name}
    >
      <div className="cp-band__in">
        {/* What this band is, top right, in the same line as the eyebrow. A
            reader scanning for the download should not have to infer it from
            a grid of squares. */}
        <div className="cp-band__head">
        <div className="cp-band__id">
          <span className="cp-band__eyebrow">{owned ? "Your shelf" : "Locked"}</span>
          <h3 className="cp-band__name"><TierName name={tier.name} /></h3>
          <p className="cp-band__q">{tier.question}</p>
          {/* No price here: Tribal Business News owns Press payment, renewal
              and upgrades, and a number embedded in this catalog goes stale
              the moment the seller changes theirs. The CTA below walks the
              reader to the canonical price. */}
          {owned || tier.id === "grove" ? null : (
            <p className="cp-band__price">Sold through Tribal Business News</p>
          )}
          {owned || tier.id !== "grove" ? null : (
            <p className="cp-band__price">${tier.price.toLocaleString("en-US")} a year</p>
          )}
          <p className="cp-band__promise">{tier.promise}</p>
          {/* "Records back to" rather than "X to present": the shelf's
              collections reach back different distances, and the panel
              beside the tiles gives each one its own dates. This line only
              promises the deepest reach. */}
          <p className="cp-band__facts">
            {entries.length} collections
            {from ? ` · records back to ${from}` : ""}
            {owned ? " · yours to download" : ""}
          </p>
        </div>
        <span className="cp-kind cp-kind--data">Collections you download</span>
        </div>

        <ul
          className="cp-band__grid"
          style={{ "--cols": Math.ceil(Math.sqrt(entries.length)) }}
        >
          {entries.map((entry, position) => (
            <Badge
              key={entry.id}
              index={position}
              entry={entry}
              open={owned}
              active={active?.id === entry.id}
              onEnter={() => setHovered(entry.id)}
              onLocked={pointAtUpgrade}
              onOpen={openTile}
            />
          ))}
        </ul>

        {owned ? (
          <p className="cp-band__all">
            <button type="button" className="cp-band__allbtn" onClick={() => { track(EVENT.shelfDownloadedAll, { shelf: tier.shelf, count: entries.length }); downloadAll(entries); }}>
              <span aria-hidden="true">&#8595;</span> Download all {entries.length}
            </button>
          </p>
        ) : null}

        {/* Live, so a screen reader hears what the cursor shows. Polite, so
            it never cuts in while someone is reading something else. */}
        <aside ref={readRef} className={`cp-read${pulse ? " is-pulse" : ""}`} aria-live="polite">
          {active ? (
            <Detail entry={active} user={user} owned={owned} />
          ) : (
            <div className="cp-read__idle">
              <span className="cp-read__cap">
                {owned ? "Your collections" : <>Inside <TierName name={tier.name} /></>}
              </span>
              <p className="cp-read__hint">
                {COARSE
                  ? "Tap a collection to see what it holds."
                  : "Point at a collection to see what it holds."}
                {owned
                  ? COARSE
                    ? " Its download is then one tap away."
                    : " Open it to explore the data and take the release."
                  : ""}
              </p>
            </div>
          )}
          {owned ? null : tier.id === "grove" ? (
            // Grove is Lumecon-sold, so its door is the app's plan page.
            <a className="cp-band__cta" href={appUrl("/app/settings?tab=plan")} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> <span aria-hidden="true">&#8594;</span>
            </a>
          ) : (
            // Press tiers are sold by Tribal Business News; /app cannot
            // perform this upgrade, so the click goes where the action lives.
            <a className="cp-band__cta" href={TBN_URL} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> at Tribal Business News{" "}
              <span aria-hidden="true">&#8594;</span>
            </a>
          )}
        </aside>
      </div>
    </section>
  );
}

/**
 * Cedar Grove, teased rather than shelved.
 *
 * Gaming Intelligence carries it, because Census and BLS are infrastructure
 * and infrastructure is not why anyone crosses this line. What Grove opens is
 * set against what a Cedar Press reader still sees, so the boundary itself is
 * the argument rather than a feature list.
 */
function GroveTeaser({ tier }) {
  const gaming = PRESS_CATALOG_BY_ID.gaming;
  const [ref, seen] = useReveal();
  return (
    // id="grove": the address of the Cedar Grove case. Article figures say
    // "Built in Cedar Grove. Make your own" and land here, on the section
    // that argues for it, rather than on the app route a Press reader
    // cannot open.
    <section ref={ref} id="grove" className={`cp-gt${seen ? " is-in" : ""}`} aria-label="Cedar Grove">
      <div className="cp-gt__head">
        <div>
          <span className="cp-sec__band">Cedar Grove</span>
          <h3 className="cp-gt__title">Ready to analyze it and share it across your organization?</h3>
          <p className="cp-gt__q">{tier.question}</p>
        </div>
        <div>
          <p className="cp-gt__body">
            Cedar Grove is the environment the collections were built for. Visualize and analyze
            across all of them at once, put the results in front of everyone you work with and
            get every dataset Lumecon builds from here as it lands.
          </p>
          {/* The price with the pitch, where deciding happens; it was a
              footnote at the bottom of the section. */}
          <p className="cp-gt__pricehead">
            ${tier.price.toLocaleString("en-US")} a year · unlimited users in one organization
          </p>
        </div>
      </div>

      <article className="cp-gt__star">
        <div className="cp-gt__starmain">
          <span className="cp-gt__excl">Cedar Grove exclusive</span>
          <h4 className="cp-gt__name">
            {gaming.name}<span className="cp-gt__and">, and more</span>
          </h4>
          <p className="cp-gt__blurb">{gaming.blurb}</p>
          <p className="cp-gt__fresh">
            {freshnessLine(gaming.id)} · {gaming.historyFrom} to present
          </p>
          <a className="cp-gt__cta" href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
            Explore Gaming Intelligence and more in Cedar Grove <span aria-hidden="true">&#8594;</span>
          </a>
        </div>
        <div className="cp-gt__split">
          <div>
            <span className="cp-gt__cap">On Cedar Press you see</span>
            <ul>{gaming.preview.shows.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
          <div>
            <span className="cp-gt__cap">Cedar Grove opens</span>
            <ul className="cp-gt__opens">
              {gaming.preview.withholds.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </div>
      </article>

      <ul className="cp-gt__caps">
        {GROVE_CAPABILITIES.map((item) => <li key={item}>{item}</li>)}
      </ul>

    </section>
  );
}

/**
 * Filtered to Data, this is a reader's own shelf and nothing else: no locked
 * band, no Cedar Grove. Somebody who asked to see the collections asked for
 * the ones they can open, and answering with an upsell is answering a
 * different question.
 */
export default function PressShelf({ user }) {
  const shelves = PRESS_TIERS.filter((tier) => tier.shelf !== "grove");
  const grove = PRESS_TIERS.find((tier) => tier.shelf === "grove");
  return (
    <div id="catalog" className="cp-bands">
      {shelves.map((tier, index) => (
        <Band key={tier.id} tier={tier} user={user} index={index} />
      ))}
      {grove ? <GroveTeaser tier={grove} /> : null}
    </div>
  );
}
